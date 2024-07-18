
import os
from config import db
from flask import Flask
from dotenv import load_dotenv
from scheduler_config import scheduler
from app.routes.bots.bots import bots_bp
from app.routes.sites.sites import sites_bp
from app.routes.slack.slack import slack_action_bp
from app.routes.keywords.keywords import keyword_bp
from app.routes.articles.articles import articles_bp
from app.routes.bots.activate import activate_bots_bp
from app.routes.bots.deactivate import deactivate_bots_bp
from app.routes.blacklist.blacklist import blacklist_bp
from app.routes.categories.categories import categories_bp
from app.routes.used_keywords.u_k import news_bots_features_bp
from app.routes.top_stories.top_stories import top_stories_bp
from app.routes.unwanted_articles.unwanted_article import unwanted_articles_bp
from app.routes.news.news import website_news_bp
from data import initialize_categories, initialize_fixed_data, initialize_keywords, initialize_sites_data

load_dotenv()

DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')


def create_app():
    app = Flask(__name__)
    app.name = 'NEWS BOT'

    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()


    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        initialize_categories()
        initialize_fixed_data()
        initialize_sites_data()
        initialize_keywords() 

    # Register blueprints -  routes
    app.register_blueprint(bots_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(blacklist_bp)
    app.register_blueprint(keyword_bp)
    app.register_blueprint(top_stories_bp)
    app.register_blueprint(unwanted_articles_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(deactivate_bots_bp)
    app.register_blueprint(slack_action_bp)
    app.register_blueprint(activate_bots_bp)
    app.register_blueprint(news_bots_features_bp)
    app.register_blueprint(website_news_bp)

    return app