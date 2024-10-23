import pytest
from app import create_app, db
from app.routes.keywords import keyword_bp
from config import Keyword, Bot
from datetime import datetime

@pytest.fixture
def app():
    app = create_app()
    if 'keyword_bp' not in app.blueprints:
        app.register_blueprint(keyword_bp)
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
    bot = Bot(
        name="Sample Bot",
        is_active=True,
        status="IDLE",
        next_run_time=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add(bot)
    db.session.commit()
    return bot

@pytest.fixture
def sample_keyword(sample_bot):
    keyword = Keyword(
        name="sample_keyword",
        bot_id=sample_bot.id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.session.add(keyword)
    db.session.commit()
    return keyword

def test_create_keywords(client, sample_bot):
    response = client.post('/keywords', json={
        'keywords': ['keyword1', 'keyword2'],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['added_count'] == 2

def test_create_keywords_invalid_data(client):
    response = client.post('/keywords', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_create_keywords_invalid_bot_ids(client, sample_bot):
    response = client.post('/keywords', json={
        'keywords': ['keyword1', 'keyword2'],
        'bot_ids': [sample_bot.id, 999]
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_delete_keywords(client, sample_keyword, sample_bot):
    response = client.delete('/keywords', json={
        'keyword_ids': [sample_keyword.id],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['deleted_count'] == 1

def test_delete_keywords_not_found(client, sample_bot):
    response = client.delete('/keywords', json={
        'keyword_ids': [999],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_delete_keywords_invalid_data(client):
    response = client.delete('/keywords', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_dynamic_search(client, sample_keyword, sample_bot):
    response = client.post('/keywords/search', json={
        'queries': ['sample'],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']['whitelist']) > 0

def test_dynamic_search_not_found(client, sample_bot):
    response = client.post('/keywords/search', json={
        'queries': ['non-existent'],
        'bot_ids': [sample_bot.id]
    })
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_dynamic_search_invalid_data(client):
    response = client.post('/keywords/search', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_extract_keywords_and_blacklist(client, tmp_path):
    # Create a sample Excel file
    excel_file = tmp_path / "test_data.xlsx"
    with open(excel_file, "wb") as f:
        f.write(b"")  # Create an empty file
    
    response = client.post('/keywords/extract', data={'file': (str(excel_file), 'test_data.xlsx')})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'keywords' in data['data']
    assert 'blacklist' in data['data']

def test_extract_keywords_and_blacklist_no_file(client):
    response = client.post('/keywords/extract')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_extract_keywords_and_blacklist_invalid_file(client, tmp_path):
    # Create an invalid file
    invalid_file = tmp_path / "invalid_test.txt"
    with open(invalid_file, "w") as f:
        f.write("This is an invalid file")
    
    response = client.post('/keywords/extract', data={'file': (str(invalid_file), 'invalid_test.txt')})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data