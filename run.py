import os
import json
from config import db
from flask_cors import CORS
from flasgger import Swagger
from flask_migrate import Migrate
from app import create_app

app = create_app()
app.app_context().push()
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

migrate = Migrate(app, db)
CORS(app, origins='*', supports_credentials=True)

app.static_folder = 'static'
app.secret_key = os.urandom(24)

if __name__ == "__main__":
    with app.app_context():
        app.run(debug=True, use_reloader=True, port=5000)
    # app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5000)
