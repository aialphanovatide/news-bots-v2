import pytest
from app.news_bot.webscrapper.init import NewsScraper

@pytest.fixture
def news_bot():
    bot = NewsScraper()
    return bot

