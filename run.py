import json
import os
from config import db
from app import create_app
from flask_cors import CORS
from flasgger import Swagger
from dotenv import load_dotenv
from flask_migrate import Migrate
from data import initialize_categories, initialize_fixed_data, initialize_keywords, initialize_sites_data

load_dotenv()

DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

app = create_app()
db_uri = app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'



swagger_template_path = os.path.join(app.root_path, 'static', 'swagger_template.json')

with open(swagger_template_path, 'r') as f:
    swagger_template = json.load(f)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)

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

if __name__ == "__main__":
    create_db(app)
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)
