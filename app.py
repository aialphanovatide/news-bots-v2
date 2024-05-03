import os
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from config import db, Bot, Category

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

# Inicializa las categorías y los datos fijos al iniciar la aplicación
with app.app_context():
    initialize_categories()
    initialize_fixed_data()

if __name__ == "__main__":
    app.run(debug=True)
