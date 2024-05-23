# from config import db_uri
# from config import Bot, db
# from datetime import datetime
# from apscheduler.schedulers.background import BackgroundScheduler
# from app.services.slack.actions import send_WARNING_message_to_slack_channel
# from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_EXECUTED

# scheduler = BackgroundScheduler(executors={'default': {'type': 'threadpool', 'max_workers': 50}})
# scheduler.add_jobstore('sqlalchemy', url=db_uri)
# logs_channel_id = "C070SM07NGL"

# if scheduler.state != 1:
#     print('-----Scheduler started-----')
#     scheduler.start()
    

# def job_executed(event):
#     job_id = str(event.job_id).capitalize()
#     scheduled_run_time = event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S')

#     print(f'\n{job_id} was executed successfully at {scheduled_run_time}, response: {event.retval}')
#     try:
#         bot = Bot.query.filter_by(name=event.job_id).first()
#         if bot:
#             bot.updated_at = datetime.now()
#             db.session.commit()
#             print(f'{job_id} updated successfully')
#         else:
#             print(f'Bot {job_id} not found in the database')
#     except Exception as e:
#         print(f'Error updating {job_id}: {str(e)}')
    

# def job_error(event):
#     job_id = str(event.job_id).capitalize()
#     error_type = event.exception.__class__.__name__
#     message = f"An error occurred in '{job_id}' - {error_type}: {event.exception}"
    
#     send_WARNING_message_to_slack_channel(channel_id=logs_channel_id, 
#                                        title_message=f"Error executing {job_id}", 
#                                        sub_title="Response", 
#                                        message=message)
    
#     print(f"Error: Job '{job_id}' raised {error_type}")
    
   
# def job_max_instances_reached(event): 
#     job_id = str(event.job_id).capitalize()
#     message = f'Maximum number of running instances reached, *Upgrade* the time interval for {job_id}'
#     send_WARNING_message_to_slack_channel(channel_id=logs_channel_id, 
#                                        title_message=f"Error executing {job_id}", 
#                                        sub_title="Response", 
#                                        message=message)
#     print(message)
  

   
# scheduler.add_listener(job_error, EVENT_JOB_ERROR)
# scheduler.add_listener(job_max_instances_reached, EVENT_JOB_MAX_INSTANCES)
# scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)