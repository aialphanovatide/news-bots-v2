from urllib.parse import urlparse
from scheduler_config import scheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.news_bot.webscrapper.init import NewsScraper
from flask import current_app
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from pytz import timezone
from config import db
import threading
import random
import pytz

def validate_url(url):
    """Validate if the URL is well-formed and contains 'news', 'google', and 'rss'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc) and 'rss' in result.path.lower()
    except:
        return False


def bot_job_function(bot, category):

    with scheduler.app.app_context():
        bot_id = bot.id
        category_id = category.id

        current_app.logger.debug(f"Starting bot job for bot: {bot.name}")

        bot.status = 'RUNNING'
        db.session.commit()

        try:
            current_app.logger.debug(f"Initializing NewsScraper for bot: {bot.name}")
            scraper = NewsScraper(url=bot.sites[0].url, bot_id=bot_id, category_id=category_id, verbose=True, debug=True)
            current_app.logger.debug(f"Running scraper for bot: {bot.name}")
            result = scraper.run()
            
            if not result['success']:
                current_app.logger.debug(f"Job for bot {bot.name} failed: {result.get('error')}")
                bot.last_run_status = 'FAILURE'
            else:
                current_app.logger.debug(f"Job for bot {bot.name} completed successfully: {result['message']}")
                bot.last_run_status = 'SUCCESS'
            
        except Exception as e:
            current_app.logger.error(f"An error occurred while running bot {bot.name}: {str(e)}")
            bot.last_run_status = 'FAILURE'
            bot.status = 'ERROR'
        else:
            bot.status = 'IDLE'
        finally:
            bot.last_run_time = datetime.now()
            bot.run_count = (bot.run_count or 0) + 1
            
            # Update next_run_time
            job = scheduler.get_job(str(bot.name))
            if job:
                bot.next_run_time = job.next_run_time.timestamp() if job.next_run_time else None
            
            db.session.commit()

def threaded_job_function(bot, category):
    thread = threading.Thread(target=bot_job_function, args=(bot, category))
    thread.start()

def schedule_bot(bot, category, fire_now=True):
    """Schedule a bot to run periodically and optionally immediately.
    
    Args:
        bot: Bot instance to be scheduled
        category: Category instance associated with the bot
        fire_now: If True, schedules an immediate run in addition to periodic schedule
    
    Returns:
        bool: True if scheduling was successful
        
    Raises:
        Exception: If there's an error during scheduling
    """
    try:
        scheduler_tz = current_app.config.get('SCHEDULER_TIMEZONE', pytz.UTC)
        bot_name = str(bot.name)
        run_frequency = int(bot.run_frequency)

        current_app.logger.info(f"Scheduling bot '{bot_name}' to run every {run_frequency} minutes")
        
        # Calculate start time with optional random delay
        initial_delay = 0 if fire_now else random.randint(0, min(run_frequency, 5))
        start_time = datetime.now(scheduler_tz) + timedelta(minutes=initial_delay)

        # Update bot status before scheduling
        bot.status = 'IDLE'
        db.session.commit()

        # Schedule periodic job
        interval_job = scheduler.add_job(
            func=bot_job_function,
            trigger=IntervalTrigger(
                minutes=run_frequency,
                timezone=scheduler_tz,
                jitter=60
            ),
            id=bot_name,
            name=bot_name,
            args=[bot, category],
            start_date=start_time,
            replace_existing=True,
            max_instances=2,
            misfire_grace_time=300  # Allow job to run up to 5 minutes late
        )
        
        # Schedule immediate run if requested
        if fire_now:
            scheduler.add_job(
                func=bot_job_function,
                trigger='date',  # Using string trigger name (more readable than DateTrigger)
                run_date=datetime.now(scheduler_tz) + timedelta(seconds=2),
                id=f"{bot_name}_immediate",
                name=f"{bot_name}_immediate",
                args=[bot, category],
                replace_existing=True
            )
            current_app.logger.debug(f"Scheduled immediate run for bot '{bot_name}'")
        
        # Update bot's next run time
        bot.next_run_time = interval_job.next_run_time
        db.session.commit()

        current_app.logger.info(
            f"Bot '{bot_name}' successfully scheduled - Next run: {interval_job.next_run_time}"
        )
        return True

    except Exception as e:
        current_app.logger.exception(f"Failed to schedule bot '{bot_name}'")
        raise

# def validate_bot_for_activation(bot, category):
#     current_app.logger.debug(f"Starting validation for bot: {bot.name}")
#     validation_errors = []

#     # Check bot fields
#     required_bot_fields = ['dalle_prompt', 'run_frequency']
#     for field in required_bot_fields:
#         if not getattr(bot, field):
#             current_app.logger.debug(f"Bot is missing {field}")
#             validation_errors.append(f"Bot is missing {field}")

#     # Check associated data
#     if not bot.sites:
#         current_app.logger.debug("Bot does not have an associated site")
#         validation_errors.append("Bot does not have an associated site")
#     elif not bot.sites[0].url:
#         current_app.logger.debug("Bot's site is missing URL")
#         validation_errors.append("Bot's site is missing URL")

#     if not bot.keywords:
#         current_app.logger.debug("Bot does not have any keywords")
#         validation_errors.append("Bot does not have any keywords")

#     if not bot.blacklist:
#         current_app.logger.debug("Bot does not have a blacklist")
#         validation_errors.append("Bot does not have a blacklist")
    
#     if category:
#         current_app.logger.debug(f"Checking category: {category.name}")
#         required_category_fields = ['slack_channel']
#         for field in required_category_fields:
#             if not getattr(category, field):
#                 current_app.logger.debug(f"Bot's category is missing {field}")
#                 validation_errors.append(f"Bot's category is missing {field}")

#     current_app.logger.debug(f"Validation complete. Errors found: {len(validation_errors)}")
#     return validation_errors


def validate_bot_for_activation(bot, category):
    """Validate if a bot has all required components for successful execution.
    
    Validates based on:
    1. Required bot fields for basic operation
    2. Required fields for DALL-E image generation
    3. Required fields for article processing
    4. Required fields for Slack notifications
    5. Site configuration for RSS feeds
    6. Keyword and blacklist configuration
    
    Args:
        bot: Bot instance to validate
        category: Category instance associated with the bot
    
    Returns:
        list: List of validation errors, empty if validation successful
    """
    validation_errors = []
    
    # Essential bot fields
    if not bot:
        return ["Bot instance is required"]
    
    current_app.logger.info(f"Validating bot '{bot.name}' (ID: {bot.id})")
    
    # Core bot configuration
    required_bot_fields = {
        'name': 'Bot name',
        'run_frequency': 'Run frequency',
        'prompt': 'Article processing prompt',
        'dalle_prompt': 'DALL-E image generation prompt'
    }
    
    for field, display_name in required_bot_fields.items():
        if not getattr(bot, field, None):
            error = f"Missing {display_name}"
            validation_errors.append(error)
            current_app.logger.error(f"Validation failed: {error}")
    
    # Site validation (RSS feed)
    if not bot.sites:
        error = "No RSS feed site configured"
        validation_errors.append(error)
        current_app.logger.error(f"Validation failed: {error}")
    elif not bot.sites[0].url:
        error = "RSS feed URL not configured"
        validation_errors.append(error)
        current_app.logger.error(f"Validation failed: {error}")
    
    # Keywords validation (required for article filtering)
    if not bot.keywords:
        error = "No keywords configured for article filtering"
        validation_errors.append(error)
        current_app.logger.error(f"Validation failed: {error}")
    
    # Blacklist validation (required for article filtering)
    if not bot.blacklist:
        error = "No blacklist configured for article filtering"
        validation_errors.append(error)
        current_app.logger.error(f"Validation failed: {error}")
    
    # Category and Slack validation
    if category:
        if not category.slack_channel:
            error = "Slack channel not configured in category"
            validation_errors.append(error)
            current_app.logger.error(f"Validation failed: {error}")
    else:
        error = "Category not configured"
        validation_errors.append(error)
        current_app.logger.error(f"Validation failed: {error}")
    
    if validation_errors:
        current_app.logger.warning(
            f"Bot '{bot.name}' validation failed with {len(validation_errors)} errors"
        )
    else:
        current_app.logger.info(f"Bot '{bot.name}' passed all validation checks")
    
    return validation_errors




