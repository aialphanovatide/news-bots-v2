from urllib.parse import urlparse
from scheduler_config import scheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.news_bot.webscrapper.init import NewsScraper
from datetime import datetime, timedelta
from config import db
import threading
import random

def validate_url(url):
    """Validate if the URL is well-formed and contains 'news' or 'google'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc)
    except:
        return False
    

def schedule_bot(bot, category):
    bot_id = bot.id
    bot_name = bot.name
    
    def bot_job_function():
        with scheduler.app.app_context():
            bot.status = 'RUNNING'
            db.session.commit()

            try:
                scraper = NewsScraper(bot_id=bot_id, category_id=category.id, verbose=True)
                result = scraper.run()
                
                if not result['success']:
                    print(f"Job for bot {bot_name} failed: {result.get('error')}")
                    bot.last_run_status = 'FAILURE'
                else:
                    print(f"Job for bot {bot_name} completed successfully: {result['message']}")
                    bot.last_run_status = 'SUCCESS'
                
            except Exception as e:
                print(f"An error occurred while running bot {bot_name}: {str(e)}")
                bot.last_run_status = 'FAILURE'
                bot.status = 'ERROR'
            else:
                bot.status = 'IDLE'
            finally:
                bot.last_run_time = datetime.now()
                bot.run_count += 1
                
                # Update next_run_time
                job = scheduler.get_job(str(bot_name))
                if job:
                    bot.next_run_time = job.next_run_time
                
                db.session.commit()

    def threaded_job_function():
        thread = threading.Thread(target=bot_job_function)
        thread.start()

    # Calculate initial delay
    initial_delay = random.randint(0, min(bot.run_frequency, 60))  # Max 60 minutes initial delay
    start_time = datetime.now() + timedelta(minutes=initial_delay)

    # Update bot's next_run_time and status
    bot.next_run_time = start_time
    bot.status = 'IDLE'
    db.session.commit()

    # Schedule the job with IntervalTrigger
    scheduler.add_job(
        threaded_job_function,
        trigger=IntervalTrigger(minutes=bot.run_frequency, start_date=start_time),
        id=str(bot_name),
        replace_existing=True
    )

    print(f"Bot {bot_name} scheduled to run every {bot.run_frequency} minutes, starting at {start_time}")
    return True  # Indicate successful scheduling


def validate_bot_for_activation(bot, category):
    validation_errors = []

    # Check bot fields
    required_bot_fields = ['dalle_prompt', 'run_frequency']
    for field in required_bot_fields:
        if not getattr(bot, field):
            validation_errors.append(f"Bot is missing {field}")

    # Check associated data
    if not bot.sites:
        validation_errors.append("Bot does not have an associated site")
    elif not bot.sites[0].url:
        validation_errors.append("Bot's site is missing URL")

    if not bot.keywords:
        validation_errors.append("Bot does not have any keywords")

    if not bot.blacklist:
        validation_errors.append("Bot does not have a blacklist")
    
    if category:
        required_category_fields = ['prompt', 'slack_channel']
        for field in required_category_fields:
            if not getattr(category, field):
                validation_errors.append(f"Bot's category is missing {field}")

    return validation_errors

# def calculate_next_execution_time(current_time, run_frequency, existing_jobs):
#     """
#     Find the best time to run a new job without overlapping other scheduled jobs.

#     This function looks at all existing jobs and finds a suitable time slot for a new job.
#     It ensures that the new job doesn't start at the same time as any existing job and
#     respects the minimum time between runs (run_frequency).

#     Args:
#         current_time (datetime): The current time, used as a starting point.
#         run_frequency (int): The minimum number of minutes that should pass between each run of this job.
#         existing_jobs (list): A list of all currently scheduled jobs from APScheduler.

#     Returns:
#         datetime: The recommended time to schedule the new job.

#     How it works:
#     1. Sort all existing jobs by their next run time.
#     2. Start looking for a free time slot from the current time.
#     3. If a time slot is too close to an existing job (less than 1 minute apart), 
#        move to the next minute and check again.
#     4. Once a free slot is found, make sure it's at least 'run_frequency' minutes from now.
#     5. Return the earliest time that satisfies all these conditions.

#     Note:
#     - This function helps prevent multiple jobs from starting at the exact same time,
#       which could overload the system.
#     - It respects the bot's run_frequency to maintain the desired schedule interval.
#     - If there are no existing jobs or all jobs are far in the future, it will return
#       a time that's exactly 'run_frequency' minutes from now.
#     """
#     # Sort existing jobs by their next execution time
#     sorted_jobs = sorted(existing_jobs, key=lambda job: job.next_run_time or current_time)
    
#     # Start with the current time
#     next_time = current_time
    
#     # Find a suitable time slot
#     while any(job.next_run_time and abs((job.next_run_time - next_time).total_seconds()) < 60 for job in sorted_jobs):
#         next_time += timedelta(minutes=20)
    
#     # Ensure the next execution time is at least run_frequency minutes from now
#     return max(next_time, current_time + timedelta(minutes=run_frequency))

# def schedule_bot(bot, category):
#     bot_id = bot.id
#     bot_name = bot.name
    
#     def job_function():
#         with scheduler.app.app_context():
#             scraper = NewsScraper(bot_id=bot_id, category_id=category.id, verbose=True)
#             result = scraper.run()
#             if not result['success']:
#                 print(f"Job for bot {bot_name} failed: {result.get('error')}")
#             else:
#                 print(f"Job for bot {bot_name} completed successfully: {result['message']}")
            
#             # Update category's updated_at timestamp
#             category.updated_at = datetime.now()
#             db.session.commit()
            
#             # Reschedule the job
#             existing_jobs = scheduler.get_jobs()
#             next_run = calculate_next_execution_time(datetime.now(), bot.run_frequency, existing_jobs)
#             scheduler.add_job(
#                 job_function,
#                 trigger='date',
#                 run_date=next_run,
#                 id=str(bot_name),
#                 replace_existing=True
#             )

#     # Schedule the initial job
#     existing_jobs = scheduler.get_jobs()
#     next_execution_time = calculate_next_execution_time(datetime.now(), bot.run_frequency, existing_jobs)
    
#     scheduler.add_job(
#         job_function,
#         trigger='date',
#         run_date=next_execution_time,
#         id=str(bot_name),
#         replace_existing=True
#     )