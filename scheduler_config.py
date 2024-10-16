from flask_apscheduler import APScheduler
from app.services.slack.actions import send_WARNING_message_to_slack_channel
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_EXECUTED
from apscheduler.triggers.cron import CronTrigger

scheduler = APScheduler()
logs_channel_id = "C070SM07NGL"

# Define event listeners within the Flask app context
def job_executed(event):
    with scheduler.app.app_context(): 
        job_id = str(event.job_id).capitalize()
        scheduled_run_time = event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S')

        scheduler.app.logger.debug(f'Job "{job_id}" was executed successfully at {scheduled_run_time}.')
        scheduler.app.logger.debug(f'Response: {event.retval}')


# Define error event listener within the Flask app context
def job_error(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        error_type = event.exception.__class__.__name__
        error_message = str(event.exception)

        formatted_message = f"[ERROR] Job '{job_id}' encountered an error:\n" \
                            f"       Type: {error_type}\n" \
                            f"       Message: {error_message}"
        
        # Log the error message to Slack (currently commented out)
        # send_warning_message_to_slack_channel(
        #     channel_id=logs_channel_id,
        #     title_message=f"Error executing {job_id}",
        #     sub_title="Response",
        #     message=formatted_message
        # )

        print(formatted_message)


# Define max instances reached event listener within the Flask app context
def job_max_instances_reached(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        message = (
            f"[WARNING] Job '{job_id}' has reached the maximum number of running instances.\n"
            f"          Consider upgrading the time interval to avoid conflicts."
        )

        # Log the warning message to Slack (currently commented out)
        # send_warning_message_to_slack_channel(
        #     channel_id=logs_channel_id,
        #     title_message=f"Max Instances Reached for {job_id}",
        #     sub_title="Response",
        #     message=message
        # )

        print(message)


def reschedule(job_id, **kwargs):
    """
    Reschedule a job with the given job_id.
    :param job_id: The ID of the job to reschedule
    :param kwargs: Additional keyword arguments to pass to the scheduler
    """
    job = scheduler.get_job(job_id)
    
    if job:
        current_trigger = job.trigger
        if isinstance(current_trigger, CronTrigger):
            new_trigger = CronTrigger(**current_trigger.fields, **kwargs)  # Reschedule with any additional kwargs
            scheduler.modify_job(job_id, trigger=new_trigger)
            
            print(f"[SUCCESS] Job '{job_id}' was rescheduled successfully with new parameters.")
        else:
            print(f"[WARNING] Job '{job_id}' does not use a CronTrigger. Rescheduling was skipped.")
    else:
        print(f"[ERROR] No job found with ID: '{job_id}'. Rescheduling failed.")



scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
scheduler.add_listener(job_error, EVENT_JOB_ERROR)
scheduler.add_listener(job_max_instances_reached, EVENT_JOB_MAX_INSTANCES)

