from flask_apscheduler import APScheduler
from app.services.slack.actions import send_WARNING_message_to_slack_channel
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_EXECUTED

scheduler = APScheduler()
logs_channel_id = "C070SM07NGL"

def job_executed(event):
    with scheduler.app.app_context(): 
        job_id = str(event.job_id).capitalize()
        scheduled_run_time = event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S')
        message = f'Job "{job_id}" was executed successfully at {scheduled_run_time}.'
        print(message)
        # send_WARNING_message_to_slack_channel(logs_channel_id, "Job Execution Success", job_id, message)

def job_error(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        error_type = event.exception.__class__.__name__
        error_message = str(event.exception)

        formatted_message = f"Job '{job_id}' encountered an error:\n" \
                            f"Type: {error_type}\n" \
                            f"Message: {error_message}"
        
        print(formatted_message)
        # send_WARNING_message_to_slack_channel(logs_channel_id, "Job Execution Error", job_id, formatted_message)

def job_max_instances_reached(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        message = (
            f"Job '{job_id}' has reached the maximum number of running instances.\n"
            f"Consider upgrading the time interval to avoid conflicts."
        )
        print(message)
        # send_WARNING_message_to_slack_channel(logs_channel_id, "Job Max Instances Reached", job_id, message)


scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
scheduler.add_listener(job_error, EVENT_JOB_ERROR)
scheduler.add_listener(job_max_instances_reached, EVENT_JOB_MAX_INSTANCES)

