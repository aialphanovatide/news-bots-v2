import pytest
from app import create_app
from app.routes.metrics.server_health_check import health_check_bp
import psutil
from datetime import datetime

@pytest.fixture
def app():
    app = create_app()
    if 'health_check_bp' not in app.blueprints:
        app.register_blueprint(health_check_bp)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.data == b'OK'