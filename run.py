import os
from config import db
# from flask import Flask
from app import create_app
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate
from dotenv import load_dotenv
# from app.routes.bots.bots import bots_bp
# from app.routes.sites.sites import sites_bp
# from app.routes.keywords.keywords import keyword_bp
# from app.routes.articles.articles import articles_bp
# from app.routes.bots.activate import activate_bots_bp
# from app.routes.blacklist.blacklist import blacklist_bp
# from app.routes.categories.categories import categories_bp
# from app.routes.used_keywords.u_k import news_bots_features_bp
# from app.routes.unwanted_articles.unwanted_article import unwanted_articles_bp
from data import initialize_categories, initialize_fixed_data, initialize_keywords, initialize_sites_data

load_dotenv()

DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

app = create_app()
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


db.init_app(app)
migrate = Migrate(app, db)
CORS(app, origins='*', supports_credentials=True)

app.static_folder = 'static'
app.secret_key = os.urandom(24)


def create_db(app):
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        initialize_categories()
        initialize_fixed_data()
        initialize_sites_data()
        initialize_keywords()

# Register blueprints -  routes
# app.register_blueprint(bots_bp)
# app.register_blueprint(categories_bp)
# app.register_blueprint(articles_bp)
# app.register_blueprint(blacklist_bp)
# app.register_blueprint(keyword_bp)
# app.register_blueprint(unwanted_articles_bp)
# app.register_blueprint(sites_bp)
# app.register_blueprint(activate_bots_bp)
# app.register_blueprint(news_bots_features_bp)
    

if __name__ == "__main__":
    create_db(app)
    app.run(debug=True, use_reloader=False)