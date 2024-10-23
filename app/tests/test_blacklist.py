import pytest
from app import create_app, db
from app.routes.blacklist import blacklist_bp
from config import Blacklist, Bot

@pytest.fixture
def app():
    app = create_app()
    if 'blacklist_bp' not in app.blueprints:
        app.register_blueprint(blacklist_bp)
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_bot():
    bot = Bot(name="Sample Bot Unique")
    db.session.add(bot)
    db.session.commit()
    return bot

@pytest.fixture
def sample_blacklist_entry(sample_bot):
    entry = Blacklist(name="Sample Entry", bot_id=sample_bot.id)
    db.session.add(entry)
    db.session.commit()
    return entry

def test_add_to_blacklist(client, sample_bot):
    response = client.post('/blacklist', json={
        'entries': ['test1', 'test2'],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['added_count'] == 2

def test_add_to_blacklist_invalid_data(client):
    response = client.post('/blacklist', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_delete_from_blacklist(client, sample_blacklist_entry):
    response = client.delete('/blacklist', json={
        'entry_ids': [sample_blacklist_entry.id],
        'bot_ids': [sample_blacklist_entry.bot_id]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['deleted_count'] == 1

def test_delete_from_blacklist_not_found(client):
    response = client.delete('/blacklist', json={
        'entry_ids': [999],
        'bot_ids': [1]
    })
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_search_blacklist(client, sample_blacklist_entry):
    response = client.post('/blacklist/search', json={
        'queries': ['Sample'],
        'bot_ids': [sample_blacklist_entry.bot_id]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']['blacklist']) > 0

def test_search_blacklist_not_found(client, sample_bot):
    response = client.post('/blacklist/search', json={
        'queries': ['NonExistent'],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data