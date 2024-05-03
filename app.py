import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from config import db
from app.routes.bots.bots import bots_bp
from app.routes.categories.categories import categories_bp

# Importa la función para inicializar las categorías desde data.py
from data import initialize_categories, initialize_fixed_data

load_dotenv()

DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}'
db.init_app(app)
migrate = Migrate(app, db)
CORS(app, origins='*', supports_credentials=True)

app.static_folder = 'static'
app.secret_key = os.urandom(24)

# Register blueprints -  routes
app.register_blueprint(bots_bp)
app.register_blueprint(categories_bp)

# Population function when init the server.
with app.app_context():
    initialize_categories()
    initialize_fixed_data()

if __name__ == "__main__":
    app.run(debug=True)
