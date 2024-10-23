import pytest
from unittest.mock import patch, Mock
from app import create_app, db
from app.routes.categories import categories_bp
from config import Category, Bot
from datetime import datetime
from app.routes.bots.utils import schedule_bot

@pytest.fixture
def app():
    app = create_app()
    if 'categories_bp' not in app.blueprints:
        app.register_blueprint(categories_bp)
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_category():
    category = Category(
        name="Sample Category",
        alias="sample-category",
        slack_channel="sample-channel",
        border_color="#000000",
        icon="https://example.com/category-icon.svg",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add(category)
    db.session.commit()
    return category

@pytest.fixture
def sample_bot(sample_category):
    bot = Bot(
        name="Sample Bot",
        category_id=sample_category.id,
        is_active=True,
        status="IDLE",
        next_run_time=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add(bot)
    db.session.commit()
    return bot

def test_create_category(client):
    response = client.post('/category', json={
        'name': 'New Category',
        'alias': 'new-category',
        'slack_channel': 'new-channel',
        'border_color': '#ffffff',
        'icon': 'new-category-icon.svg'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['name'] == 'New Category'

def test_create_category_missing_fields(client):
    response = client.post('/category', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_create_category_duplicate(client, sample_category):
    response = client.post('/category', json={
        'name': sample_category.name,
        'alias': sample_category.alias
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_delete_category(client, sample_category):
    response = client.delete(f'/category/{sample_category.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['deleted_id'] == sample_category.id

def test_delete_category_not_found(client):
    response = client.delete('/category/999')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_get_categories(client, sample_category, sample_bot):
    response = client.get('/categories')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']['categories']) > 0
    assert data['data']['categories'][0]['bots']

def test_get_categories_empty(client):
    response = client.get('/categories')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_get_category(client, sample_category):
    response = client.get(f'/category?category_id={sample_category.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['category']['id'] == sample_category.id

def test_get_category_by_name(client, sample_category):
    response = client.get(f'/category?category_name={sample_category.name}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['category']['name'] == sample_category.name

def test_get_category_missing_params(client):
    response = client.get('/category')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_get_category_not_found(client):
    response = client.get('/category?category_id=999')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

@patch('app.routes.categories.schedule_bot')
def test_update_category(mock_schedule_bot, client, sample_category, sample_bot):
    mock_schedule_bot.return_value = True
    response = client.put(f'/category/{sample_category.id}', json={
        'name': 'Updated Category',
        'alias': 'updated-category',
        'slack_channel': 'updated-channel',
        'border_color': '#123456'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['category']['name'] == 'Updated Category'
    assert data['data']['rescheduled_bots'] == ['Sample Bot']

def test_update_category_not_found(client):
    response = client.put('/category/999', json={'name': 'Updated Category'})
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_toggle_category_activation(client, sample_category, sample_bot):
    response = client.post(f'/category/{sample_category.id}/toggle-activation')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['activated_count'] == 1
    assert data['data']['deactivated_count'] == 0

def test_toggle_category_activation_missing_category(client):
    response = client.post('/category/999/toggle-activation')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data