from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    alias = db.Column(db.String)
    time_interval = db.Column(db.Integer)  # Nueva columna
    icon = db.Column(db.String)  # Nueva columna
    is_active = db.Column(db.Boolean)
    border_color = db.Column(db.String)
    created_at = db.Column(db.TIMESTAMP)

    def __repr__(self):
        return f"Category(category_id={self.category_id}, category={self.category}, category_name={self.category_name}, time_interval={self.time_interval}, icon={self.icon}, is_active={self.is_active}, border_color={self.border_color}, created_at={self.created_at})"

class Bot(db.Model):
    __tablename__ = 'bot'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    # relationships
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


class Site(db.Model):
    __tablename__ = 'site'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    url = db.Column(db.String)

    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))

    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


class Keyword(db.Model):
    __tablename__ = 'keyword'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


class Article(db.Model):
    __tablename__ = 'article'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String)
    content = db.Column(db.String)
    analysis = db.Column(db.String)
    url = db.Column(db.String)
    date = db.Column(db.TIMESTAMP)
    used_keywords = db.Column(db.String)
    is_article_efficent = db.Column(db.String)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))
    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)


class UnwantedArticle(db.Model):
    __tablename__ = 'unwanted_article'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String)
    content = db.Column(db.String)
    analysis = db.Column(db.String)
    url = db.Column(db.String)
    date = db.Column(db.TIMESTAMP)
    used_keywords = db.Column(db.String)
    is_article_efficent = db.Column(db.String)
    # relationship
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'))

    created_at = db.Column(db.TIMESTAMP)
    updated_at = db.Column(db.TIMESTAMP)
    