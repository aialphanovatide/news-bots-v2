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
    """Validate if the URL is well-formed and contains 'news' or 'google'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc)
    except:
        return False


def bot_job_function(bot, category):
    from app import scheduler  # Import here to avoid circular imports
    with scheduler.app.app_context():
        bot_id = bot.id
        category_id = category.id

        bot.status = 'RUNNING'
        db.session.commit()

        try:
            scraper = NewsScraper(url=bot.sites[0].url, bot_id=bot_id, category_id=category_id, verbose=True)
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
    from app import scheduler  # Import here to avoid circular imports
    try:
        # Get the scheduler timezone from app config
        scheduler_tz = current_app.config.get('SCHEDULER_TIMEZONE') or pytz.UTC

        bot_id = bot.id
        bot_name = str(bot.name)

        current_app.logger.debug(f"Scheduling bot: {bot_name}")
        current_app.logger.debug(f"Bot ID: {bot_id}")
        current_app.logger.debug(f"Bot name: {bot_name}")
        
        run_frequency = int(bot.run_frequency)
        
        # Calculate initial delay
        initial_delay = 0 if fire_now else random.randint(0, min(run_frequency, 5))
        start_time = datetime.now(scheduler_tz) + timedelta(minutes=initial_delay)

        # Update bot's status
        bot.status = 'IDLE'
        db.session.commit()

        # Schedule the job with IntervalTrigger
        try:
            interval_job =scheduler.add_job(
                id=bot_name,
                func=threaded_job_function,
                trigger=IntervalTrigger(
                    minutes=run_frequency,
                    timezone=scheduler_tz,
                    jitter=60  # Add a jitter of up to 60 seconds
                ),
                start_date=start_time,
                name=bot_name,
                args=[bot, category],
                replace_existing=True,
                max_instances=2,
                jobstore='default'
            )

            if fire_now:
                immediate_job = scheduler.add_job(
                    id=bot_name,
                    func=threaded_job_function,
                    trigger=DateTrigger(
                        run_date=datetime.now(scheduler_tz),
                        timezone=scheduler_tz
                    ),
                    name=bot_name,
                    args=[bot, category],
                    replace_existing=True,
                    jobstore='default'
                )
                current_app.logger.debug(f"Bot {bot_name} scheduled to run immediately for testing")
                bot.next_run_time = immediate_job.next_run_time

            # Update bot's next_run_time with the actual next run time
            if fire_now:
                # If fire_now is True, the next run will be from the interval job
                bot.next_run_time =  interval_job.next_run_time
            else:
                # If fire_now is False, use the next_run_time from the interval job
                bot.next_run_time = interval_job.next_run_time

        except Exception as e:
            current_app.logger.error(f"Error adding job for bot {bot_name}: {str(e)}")
            raise  # Re-raise the exception to be handled by the caller

        current_app.logger.debug(f"Bot {bot_name} scheduled to run every {run_frequency} minutes, starting at {start_time}")
        return True  # Indicate successful scheduling

    except Exception as e:
        current_app.logger.error(f"Error scheduling bot {bot_name}: {str(e)}")
        raise  # Re-raise the exception so the calling function can handle it 



def validate_bot_for_activation(bot, category):
    current_app.logger.debug(f"Starting validation for bot: {bot.name}")
    validation_errors = []

    # Check bot fields
    required_bot_fields = ['dalle_prompt', 'run_frequency']
    for field in required_bot_fields:
        if not getattr(bot, field):
            current_app.logger.debug(f"Bot is missing {field}")
            validation_errors.append(f"Bot is missing {field}")

    # Check associated data
    if not bot.sites:
        current_app.logger.debug("Bot does not have an associated site")
        validation_errors.append("Bot does not have an associated site")
    elif not bot.sites[0].url:
        current_app.logger.debug("Bot's site is missing URL")
        validation_errors.append("Bot's site is missing URL")

    if not bot.keywords:
        current_app.logger.debug("Bot does not have any keywords")
        validation_errors.append("Bot does not have any keywords")

    if not bot.blacklist:
        current_app.logger.debug("Bot does not have a blacklist")
        validation_errors.append("Bot does not have a blacklist")
    
    if category:
        current_app.logger.debug(f"Checking category: {category.name}")
        required_category_fields = ['prompt', 'slack_channel']
        for field in required_category_fields:
            if not getattr(category, field):
                current_app.logger.debug(f"Bot's category is missing {field}")
                validation_errors.append(f"Bot's category is missing {field}")

    current_app.logger.debug(f"Validation complete. Errors found: {len(validation_errors)}")
    return validation_errors





