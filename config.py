from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

db = SQLAlchemy()
load_dotenv()

DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

db_uri = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    alias = db.Column(db.String)
    slack_channel = db.Column(db.String)
    time_interval = db.Column(db.Integer)  
    icon = db.Column(db.String) 
    prompt = db.Column(db.String)
    is_active = db.Column(db.Boolean)
    border_color = db.Column(db.String)
    updated_at = db.Column(db.TIMESTAMP)
    created_at = db.Column(db.TIMESTAMP)

    bots = db.relationship("Bot", backref="category", cascade="all, delete-orphan")

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Bot(db.Model):
    __tablename__ = 'bot'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    dalle_prompt = db.Column(db.String)
    # relationships
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    sites = db.relationship("Site", backref="bot", cascade="all, delete-orphan")
    keywords = db.relationship("Keyword", backref="bot", cascade="all, delete-orphan")
    blacklist = db.relationship("Blacklist", backref="bot", cascade="all, delete-orphan")
    articles = db.relationship("Article", backref="bot", cascade="all, delete-orphan")
    unwanted_articles = db.relationship("UnwantedArticle", backref="bot", cascade="all, delete-orphan")

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Site(db.Model):
    __tablename__ = 'site'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    url = db.Column(db.String)

    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))

    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Keyword(db.Model):
    __tablename__ = 'keyword'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Article(db.Model):
    """
    Represents an article in the database.

    Attributes:
        id (int): Primary key, auto-incremented.
        title (str): Title of the article.
        content (str): Content of the article.
        image (str): URL or path to the image associated with the article.
        analysis (str): Analysis data of the article.
        url (str): URL of the article.
        date (datetime): Timestamp when the article was published.
        used_keywords (str): Keywords used in the article.
        is_article_efficent (str): Flag to indicate if the article is efficient.
        is_top_story (bool): Flag to indicate if the article is a top story.
        bot_id (int): Foreign key referencing the bot that created the article.
        created_at (datetime): Timestamp when the article was created.
        updated_at (datetime): Timestamp when the article was last updated.
    """
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String)
    content = db.Column(db.String)
    image = db.Column(db.String)
    analysis = db.Column(db.String)
    url = db.Column(db.String)
    date = db.Column(db.TIMESTAMP)
    used_keywords = db.Column(db.String)
    is_article_efficent = db.Column(db.String)
    is_top_story = db.Column(db.Boolean)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class UnwantedArticle(db.Model):
    __tablename__ = 'unwanted_article'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String)
    content = db.Column(db.String)
    reason = db.Column(db.String)
    url = db.Column(db.String)
    date = db.Column(db.TIMESTAMP)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    

class UsedKeywords(db.Model):
    __tablename__ = 'used_keywords'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_content = db.Column(db.String)
    article_date = db.Column(db.TIMESTAMP)
    article_url = db.Column(db.String)
    keywords = db.Column(db.String)
    source = db.Column(db.String)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
