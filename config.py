from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import Enum
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func

load_dotenv()
db = SQLAlchemy()

DB_URI = os.getenv('DB_URI')

# Configure the engine with the timezone
engine = create_engine(
    DB_URI, 
    pool_size=30, 
    max_overflow=20,
    connect_args={"options": "-c timezone=America/Argentina/Buenos_Aires"}
)
print(f"Connected to {DB_URI}")
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Category(db.Model):
    """Represents a category in the database.

    Attributes:
        id (int): The unique identifier for the category.
        name (str): The name of the category.
        alias (str): An alias for the category.
        slack_channel (str): The Slack channel linked to the category.
        icon (str): The icon representing the category.
        border_color (str): The border color for the category.
        is_active (bool): Indicates if the category is active.
        created_at (datetime): The timestamp when the category was created.
        updated_at (datetime): The timestamp when the category was last updated.
        bots (relationship): Relationship to Bot model, representing bots in this category.

    Methods:
        as_dict(): Returns a dictionary representation of the category.
    """
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    alias = db.Column(db.String, nullable=False)
    slack_channel = db.Column(db.String)
    icon = db.Column(db.String)
    border_color = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.TIMESTAMP, default=func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    bots = db.relationship("Bot", backref="category", cascade="all, delete-orphan")

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Bot(db.Model):
    """Represents a bot in the database.

    Attributes:
        id (int): The unique identifier for the bot.
        name (str): The name of the bot.
        alias (str): An alias for the bot.
        dalle_prompt (str): The prompt for DALL-E associated with the bot.
        prompt (str): The prompt for the bot.
        icon (str): The icon representing the bot.
        background_color (str): The background color for the bot.
        run_frequency (str): The frequency at which the bot runs.
        is_active (bool): Indicates if the bot is active.
        category_id (int): Foreign key referencing the category the bot belongs to.
        created_at (datetime): The timestamp when the bot was created.
        updated_at (datetime): The timestamp when the bot was last updated.
        next_run_time (datetime): The scheduled time for the bot's next run.
        status (str): The current status of the bot, can be 'IDLE', 'RUNNING', or 'ERROR'.
        last_run_time (datetime): The timestamp of the bot's last run.
        last_run_status (str): The status of the bot's last run, can be 'SUCCESS' or 'FAILURE'.
        run_count (int): The total number of times the bot has run.
    """
    __tablename__ = 'bot'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    alias = db.Column(db.String)
    dalle_prompt = db.Column(db.String(1024))
    prompt = db.Column(db.Text)
    icon  = db.Column(db.String)
    background_color = db.Column(db.String)
    run_frequency = db.Column(db.String, default='20')
    is_active = db.Column(db.Boolean, default=False)
    next_run_time = db.Column(db.DateTime)
    status = db.Column(Enum('IDLE', 'RUNNING', 'ERROR', name='bot_status'), default='IDLE')
    last_run_time = db.Column(db.DateTime)
    last_run_status = db.Column(Enum('SUCCESS', 'FAILURE', name='run_status'))
    run_count = db.Column(db.Integer, default=0)
    
    # relationships
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)

    sites = db.relationship("Site", backref="bot", cascade="all, delete-orphan")
    keywords = db.relationship("Keyword", backref="bot", cascade="all, delete-orphan")
    blacklist = db.relationship("Blacklist", backref="bot", cascade="all, delete-orphan")
    articles = db.relationship("Article", backref="bot", cascade="all, delete-orphan")
    unwanted_articles = db.relationship("UnwantedArticle", backref="bot", cascade="all, delete-orphan")
    metrics = db.relationship("Metrics", back_populates="bot", cascade="all, delete-orphan")

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Site(db.Model):
    """Represents a site associated with a bot.

    Attributes:
        id (int): The unique identifier for the site.
        name (str): The name of the site.
        url (str): The URL of the site.
        bot_id (int): Foreign key referencing the bot associated with the site.
        created_at (datetime): The timestamp when the site was created.
        updated_at (datetime): The timestamp when the site was last updated.
    """
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
    """Represents a keyword associated with a bot.

    Attributes:
        id (int): The unique identifier for the keyword.
        name (str): The name of the keyword.
        bot_id (int): Foreign key referencing the bot associated with the keyword.
        created_at (datetime): The timestamp when the keyword was created.
        updated_at (datetime): The timestamp when the keyword was last updated.
    """
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
    """Represents a blacklist entry associated with a bot.

    Attributes:
        id (int): The unique identifier for the blacklist entry.
        name (str): The name of the blacklist entry.
        bot_id (int): Foreign key referencing the bot associated with the blacklist entry.
        created_at (datetime): The timestamp when the blacklist entry was created.
        updated_at (datetime): The timestamp when the blacklist entry was last updated.
    """
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
    """Represents an article in the database.

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
    """Represents an unwanted article in the database.

    Attributes:
        id (int): The unique identifier for the unwanted article.
        title (str): Title of the unwanted article.
        content (str): Content of the unwanted article.
        reason (str): Reason for the article being unwanted.
        url (str): URL of the unwanted article.
        date (datetime): Timestamp when the article was identified as unwanted.
        bot_id (int): Foreign key referencing the bot that flagged the article.
        created_at (datetime): Timestamp when the unwanted article was created.
        updated_at (datetime): Timestamp when the unwanted article was last updated.
    """
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
    """Represents keywords used in articles.

    Attributes:
        id (int): The unique identifier for the used keywords entry.
        article_content (str): Content of the article associated with the keywords.
        article_date (datetime): Date of the article associated with the keywords.
        article_url (str): URL of the article associated with the keywords.
        keywords (str): The keywords used in the article.
        source (str): The source of the keywords.
        article_id (int): Foreign key referencing the article associated with the keywords.
        bot_id (int): Foreign key referencing the bot associated with the keywords.
        created_at (datetime): Timestamp when the used keywords entry was created.
    """
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


class Metrics(db.Model):
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id', ondelete='CASCADE'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    total_runtime = db.Column(db.Float)
    total_articles_found = db.Column(db.Integer, default=0)
    articles_processed = db.Column(db.Integer, default=0)
    articles_saved = db.Column(db.Integer, default=0)
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    total_errors = db.Column(db.Integer, default=0)
    error_reasons = db.Column(db.JSON)
    total_filtered = db.Column(db.Integer, default=0)
    filter_reasons = db.Column(db.JSON)

    # Define the relationship with the Bot model
    bot = db.relationship('Bot', back_populates='metrics')

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}