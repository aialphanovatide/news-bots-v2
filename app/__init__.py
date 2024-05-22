
from flask import Flask
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
from app.routes.unwanted_articles.unwanted_article import unwanted_articles_bp


def create_app():
    app = Flask(__name__)
    app.name = 'NEWS BOT'

    # Register blueprints -  routes
    app.register_blueprint(bots_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(blacklist_bp)
    app.register_blueprint(keyword_bp)
    app.register_blueprint(unwanted_articles_bp)
    app.register_blueprint(sites_bp)
    app.register_blueprint(deactivate_bots_bp)
    app.register_blueprint(slack_action_bp)
    app.register_blueprint(activate_bots_bp)
    app.register_blueprint(news_bots_features_bp)

    return app