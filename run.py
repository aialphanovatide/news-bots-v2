import os
import json
from config import db
from app import create_app
from flask_cors import CORS
from flasgger import Swagger
from flask_migrate import Migrate
from app import create_app


app = create_app()

swagger_template_path = os.path.join(app.root_path, 'static', 'swagger.json')

with open(swagger_template_path, 'r') as f:
    swagger_template = json.load(f)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'swagger',
            "route": '/swagger.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
    "title": "News Bot API",
    "swagger_ui_config": {
        "docExpansion": "none",
        "tagsSorter": "alpha"
    }
}


swagger = Swagger(app, template=swagger_template, config=swagger_config)
migrate = Migrate(app, db)
CORS(app, origins='*', supports_credentials=True)

app.static_folder = 'static'
app.secret_key = os.urandom(24)


if __name__ == "__main__":
    try:
        print("Starting the server...")
        app.run(debug=False, use_reloader=False, port=5002, threaded=True, host='0.0.0.0')
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Server has stopped.")
