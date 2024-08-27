from flask_apscheduler import APScheduler
from config import db_uri, Bot, db
from datetime import datetime
from app.services.slack.actions import send_WARNING_message_to_slack_channel
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_EXECUTED
from apscheduler.triggers.cron import CronTrigger

# Configuración para FlaskAPScheduler
class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': db_uri
        }
    }
    SCHEDULER_EXECUTORS = {
        'default': {
            'type': 'threadpool',
            'max_workers': 50
        }
    }

scheduler = APScheduler()

# ID del canal de logs en Slack
logs_channel_id = "C070SM07NGL"

# Comprobar si el scheduler ya está iniciado
if scheduler.state != 1:
    print('-----Scheduler started-----')

# Define event listeners within the Flask app context
def job_executed(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        scheduled_run_time = event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S')
        print(f'\n{job_id} was executed successfully at {scheduled_run_time}, response: {event.retval}')
        try:
            bot = Bot.query.filter_by(name=event.job_id).first()
            if bot:
                bot.updated_at = datetime.now()
                db.session.commit()
                print(f'{job_id} updated successfully')
            else:
                print(f'Bot {job_id} not found in the database')
        except Exception as e:
            print(f'Error updating {job_id}: {str(e)}')

def job_error(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        error_type = event.exception.__class__.__name__
        message = f"An error occurred in '{job_id}' - {error_type}: {event.exception}"
        # Aquí podrías enviar un mensaje a Slack en caso de error
        # send_WARNING_message_to_slack_channel(
        #     channel_id=logs_channel_id,
        #     title_message=f"Error executing {job_id}",
        #     sub_title="Response",
        #     message=message
        # )
        print(f"Error: Job '{job_id}' raised {error_type}")

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
            new_trigger = CronTrigger(**current_trigger.fields)
            scheduler.modify_job(job_id, trigger=new_trigger)
            print(f"Job {job_id} rescheduled successfully")
        else:
            print(f"Warning: Job {job_id} does not have a CronTrigger. Rescheduling skipped.")
    else:
        print(f"No job found with ID: {job_id}")

def job_max_instances_reached(event):
    with scheduler.app.app_context():
        job_id = str(event.job_id).capitalize()
        message = f'Maximum number of running instances reached, *Upgrade* the time interval for {job_id}'
        # Aquí podrías enviar un mensaje a Slack en caso de que se alcance el máximo de instancias
        # send_WARNING_message_to_slack_channel(
        #     channel_id=logs_channel_id,
        #     title_message=f"Error executing {job_id}",
        #     sub_title="Response",
        #     message=message
        # )
        print(message)

# Añadir listeners para los eventos
scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
scheduler.add_listener(job_error, EVENT_JOB_ERROR)
scheduler.add_listener(job_max_instances_reached, EVENT_JOB_MAX_INSTANCES)
