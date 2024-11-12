
from scheduler_config import scheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.news_bot.news_bot_v2 import NewsProcessingPipeline
from datetime import datetime, timedelta
from flask import current_app
from config import db
import random
import pytz
import asyncio

def bot_job_function(bot, category):
    with scheduler.app.app_context():
        current_app.logger.debug(f"Starting bot job for bot: {bot.name}")

        bot.status = 'RUNNING'
        db.session.commit()

        try:
            current_app.logger.debug(f"Initializing NewsScraper for bot: {bot.name}")
            scraper = NewsProcessingPipeline(
                url=bot.sites[0].url,
                bot=bot,
                category=category,
            )
            
            current_app.logger.debug(f"Running scraper for bot: {bot.name}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(scraper.run())
            finally:
                loop.close()
            
            if not result['success']:
                current_app.logger.debug(f"Job for bot {bot.name} failed: {result.get('message', 'Unknown error')}")
                bot.last_run_status = 'FAILURE'
            else:
                current_app.logger.debug(f"Job for bot {bot.name} completed successfully: {result.get('message', 'Success')}, results: {result.get('processed_items', 'No results')}")
                bot.last_run_status = 'SUCCESS'
            
        except Exception as e:
            current_app.logger.error(f"An error occurred while running bot {bot.name}: {str(e)}")
            bot.last_run_status = 'FAILURE'
            bot.status = 'ERROR'
            raise
        else:
            bot.status = 'IDLE'
        finally:
            bot.last_run_time = datetime.now()
            bot.run_count = (bot.run_count or 0) + 1
            
            job = scheduler.get_job(str(bot.name))
            if job and job.next_run_time:
                bot.next_run_time = job.next_run_time.replace(tzinfo=None)
            
            db.session.commit()

def schedule_bot(bot, category, fire_now):
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
                trigger='date',
                run_date=datetime.now(scheduler_tz) + timedelta(seconds=5),
                id=f"{bot_name}_immediate",
                name=f"{bot_name}_immediate",
                args=[bot, category],
                replace_existing=True
            )
            current_app.logger.debug(f"Scheduled immediate run for Bot: {bot_name}")  
        
        # Update bot's next run time - Store as datetime
        if interval_job.next_run_time:
            next_run_time = interval_job.next_run_time.astimezone(scheduler_tz)
            bot.next_run_time = next_run_time.replace(tzinfo=None)  # Remove timezone info for DB storage
            db.session.commit()

        current_app.logger.debug(f"Bot {bot_name} successfully scheduled - Next run: {next_run_time}")
        return True

    except Exception as e:
        raise Exception(f"Failed to schedule bot '{bot_name}': {str(e)}")


