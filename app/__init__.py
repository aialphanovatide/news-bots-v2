import os
from flask import Flask
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv
from pytz import timezone
from config import db
from scheduler_config import scheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from app.routes.bots.bot_scheduler import cleanup_news_bot_logs
from app.utils.timezones import check_server_timezone, check_database_timezone, check_scheduler_timezone

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
upload_folder = os.path.join(basedir, 'static', 'TempUploads')

# Ensure the upload folder exists
os.makedirs(upload_folder, exist_ok=True)

# Load environment variables
DB_URI = os.getenv('DB_URI')

# Configuration
class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = timezone('America/Argentina/Buenos_Aires')

def create_app():
    app = Flask(__name__)
    app.name = 'NEWS BOT API'
    app.config.from_object(Config)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Initialize database
    db.init_app(app)

    # Scheduler configuration
    app.config['SCHEDULER_JOBSTORES'] = {
        'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
    }
    app.config['SCHEDULER_EXECUTORS'] = {
        'default': {
            'type': 'threadpool',
            'max_workers': 50
        }
    }

    # Initialize and start scheduler
    scheduler.init_app(app)
    if scheduler.state != 1:
        print('Scheduler started')
        scheduler.start()

    with app.app_context():
        # Add job to cleanup news bot logs
        scheduler.add_job(
            func=cleanup_news_bot_logs,
            trigger=CronTrigger(
                day_of_week='sun',
                hour=0,
                minute=0
            ),
            # Uncomment this line if you want to use execute the job immediately
            # trigger=DateTrigger(),
            id='weekly_log_cleanup',
            name='Weekly News Bot Log Cleanup',
            replace_existing=True
        )
    
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        check_server_timezone()
        check_database_timezone()
        check_scheduler_timezone()
          

    # Register blueprints
    from app.routes.bots.bots import bots_bp
    from app.routes.keywords.keywords import keyword_bp
    from app.routes.articles.articles import articles_bp
    from app.routes.bots.activate import activate_bots_bp
    from app.routes.bots.deactivate import deactivate_bots_bp
    from app.routes.blacklist.blacklist import blacklist_bp
    from app.routes.categories.categories import categories_bp
    from app.routes.used_keywords.u_k import news_bots_features_bp
    from app.routes.top_stories.top_stories import top_stories_bp
    from app.routes.unwanted_articles.unwanted_article import unwanted_articles_bp
    from app.routes.image_generation.image_generation import image_generation_bp
    from app.routes.metrics.server_health_check import health_check_bp

    blueprints = [
        bots_bp, categories_bp, articles_bp, blacklist_bp, keyword_bp,
        top_stories_bp, unwanted_articles_bp, deactivate_bots_bp,
        image_generation_bp,
        activate_bots_bp, news_bots_features_bp,health_check_bp
    ]

    for blueprint in blueprints:
        app.register_blueprint(blueprint)

    # Uncomment these lines if you need to initialize data
    from data import initialize_categories, initialize_fixed_data, initialize_keywords, initialize_sites_data
    with app.app_context():
        initialize_categories()
        initialize_fixed_data()
        initialize_sites_data()
        initialize_keywords()

    return app

