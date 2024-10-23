import pytest
from app import create_app, db
from app.routes.articles.articles import articles_bp
from config import Article, Bot, UnwantedArticle

@pytest.fixture
def app():
    app = create_app()  # Usa la función create_app para crear la aplicación
    
    # Check if the blueprint is already registered before registering it
    if 'articles_bp' not in app.blueprints:
        app.register_blueprint(articles_bp)
    
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()  # Crear las tablas
        yield app
        db.drop_all()  # Limpiar después de las pruebas

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def sample_bot():
    bot = Bot(name="Sample Bot Unique")  # Ensure the name is unique
    db.session.add(bot)
    db.session.commit()
    return bot

@pytest.fixture
def sample_article():
    article = Article(title="Sample Article", content="This is a sample article.", bot_id=1)
    db.session.add(article)
    db.session.commit()
    return article

def test_get_all_articles(client):
    response = client.get('/articles')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert isinstance(data['data'], list)

def test_get_article_by_id(client, sample_article):
    response = client.get(f'/article/{sample_article.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data']['title'] == "Sample Article"

def test_get_article_by_id_not_found(client):
    response = client.get('/article/999')  # ID que no existe
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'No article found for the specified article ID in either Article or UnwantedArticle table'

def test_get_articles_by_bot(client):
    bot = Bot(name="Sample Bot")
    db.session.add(bot)
    db.session.commit()
    
    article = Article(title="Bot Article", content="This article is from a bot.", bot_id=bot.id)
    db.session.add(article)
    db.session.commit()

    response = client.get(f'/article?bot_id={bot.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['data']) > 0

def test_delete_article(client, sample_article):
    response = client.delete(f'/article/{sample_article.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['message'] == 'Article deleted successfully'

def test_delete_article_not_found(client):
    response = client.delete('/article/999')  # ID que no existe
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Article not found'

def test_get_all_articles_empty(client):
    response = client.get('/articles')
    assert response.status_code == 204  # No content
    data = response.get_json()
    assert data['success'] is True
    assert data['data'] == []

def test_get_articles_by_bot_missing_params(client):
    response = client.get('/article')
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'Missing bot ID or bot name in request data'

def test_get_all_articles_empty(client):
    response = client.get('/articles')
    assert response.status_code == 204  # No content
    # Check if the response data is empty
    try:
        data = response.get_json()
    except Exception as e:
        data = None  # Handle the case where JSON decoding fails
    assert data is None  # Ensure that 