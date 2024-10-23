import pytest
from unittest.mock import patch
from app import create_app
from app.routes.openai import openai_bp
from app.routes.routes_utils import create_response
from sqlalchemy.exc import SQLAlchemyError
import os

@pytest.fixture
def app():
    app = create_app()
    if 'openai_bp' not in app.blueprints:
        app.register_blueprint(openai_bp)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_usage_success(client, monkeypatch):
    def mock_get_openai_usage(api_key):
        return {'total_tokens': 1000, 'total_cost': 0.5}

    monkeypatch.setattr('os.getenv', lambda x: 'test_api_key')
    monkeypatch.setattr('app.services.api_monitor.openai.get_openai_usage', mock_get_openai_usage)

    response = client.get('/api/openai-usage')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'data' in data
    assert data['data']['total_tokens'] == 1000
    assert data['data']['total_cost'] == 0.5

def test_get_usage_openai_error(client, monkeypatch):
    def mock_get_openai_usage(api_key):
        return {'error': 'OpenAI API error'}

    monkeypatch.setattr('os.getenv', lambda x: 'test_api_key')
    monkeypatch.setattr('app.services.api_monitor.openai.get_openai_usage', mock_get_openai_usage)

    response = client.get('/api/openai-usage')
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] is False
    assert 'error' in data

def test_get_usage_database_error(client, monkeypatch):
    def mock_get_openai_usage(api_key):
        raise SQLAlchemyError('Database error')

    monkeypatch.setattr('os.getenv', lambda x: 'test_api_key')
    monkeypatch.setattr('app.services.api_monitor.openai.get_openai_usage', mock_get_openai_usage)

    response = client.get('/api/openai-usage')
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] is False
    assert 'error' in data

def test_get_usage_general_error(client, monkeypatch):
    def mock_get_openai_usage(api_key):
        raise Exception('General error')

    monkeypatch.setattr('os.getenv', lambda x: 'test_api_key')
    monkeypatch.setattr('app.services.api_monitor.openai.get_openai_usage', mock_get_openai_usage)

    response = client.get('/api/openai-usage')
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] is False
    assert 'error' in data