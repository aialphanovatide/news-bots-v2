import time
from config import db
from sqlalchemy import text
from flask import current_app
from scheduler_config import scheduler

def check_server_timezone():
    print(f"Server timezone: {time.tzname}")

def check_database_timezone():
    with current_app.app_context():
        result = db.session.execute(text("SHOW TIME ZONE")).scalar()
        print(f"Database timezone: {result}")

def check_scheduler_timezone():
    with current_app.app_context():
        scheduler_timezone = current_app.config.get('SCHEDULER_TIMEZONE')
        print(f"APScheduler timezone: {scheduler_timezone}")