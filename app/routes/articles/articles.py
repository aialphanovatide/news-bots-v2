import os
from flask import Blueprint, jsonify, request
from app.routes.routes_utils import create_response, handle_db_session
from config import Article, Bot, db
from redis_client.redis_client import cache_with_redis, update_cache_with_redis

articles_bp = Blueprint('articles_bp', __name__, template_folder='templates', static_folder='static')

@articles_bp.route('/articles', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_all_articles():
    """
    Retrieve all articles with an optional limit.
    
    Returns:
        JSON response with the list of articles or an error message.
    """
    limit = request.args.get('limit', default=10, type=int)
    if limit < 1:
        response = create_response(error='Limit must be a positive integer')
        return jsonify(response), 400

    articles = Article.query.order_by(Article.created_at.desc()).limit(limit).all()
    if not articles:
        response = create_response(success=True, data=[], error='No articles found')
        return jsonify(response), 404

    response = create_response(success=True, data=[article.as_dict() for article in articles])
    return jsonify(response), 200


@articles_bp.route('/article/<int:article_id>', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID.
    
    Args:
        article_id (int): The ID of the article to retrieve.
    
    Returns:
        JSON response with the article data or an error message.
    """
    article = Article.query.filter_by(id=article_id).first()
    if not article:
        response = create_response(error='No article found for the specified article ID')
        return jsonify(response), 404

    response = create_response(success=True, data=article.as_dict())
    return jsonify(response), 200


@articles_bp.route('/articles', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_articles_by_bot():
    """
    Retrieve articles by bot ID or bot name with an optional limit.
    
    Returns:
        JSON response with the list of articles or an error message.
    """
    bot_id = request.args.get('bot_id')
    bot_name = request.args.get('bot_name')
    limit = request.args.get('limit', default=10, type=int)

    if not bot_id and not bot_name:
        response = create_response(error='Missing bot ID or bot name in request data')
        return jsonify(response), 400

    if bot_name:
        bot = Bot.query.filter_by(name=bot_name).first()
        if not bot:
            response = create_response(error='No bot found with the specified bot name')
            return jsonify(response), 404
        bot_id = bot.id

    articles = Article.query.filter_by(bot_id=bot_id).order_by(Article.created_at.desc()).limit(limit).all()
    if not articles:
        response = create_response(error='No articles found for the specified bot ID')
        return jsonify(response), 404

    response = create_response(success=True, data=[article.as_dict() for article in articles])
    return jsonify(response), 200



@articles_bp.route('/articles', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_all_articles','get_article_by_id','get_articles_by_bot'])
@handle_db_session
def delete_article():
    """
    Delete an article by its ID.
    
    Args:
        article_id (int): The ID of the article to delete.
    
    Returns:
        JSON response with the success status or an error message.
    """
    article_id = request.args.get('article_id')
    if not article_id:
        response = create_response(error='Article ID missing in request data')
        return jsonify(response), 400

    article = Article.query.get(article_id)
    if article:
        db.session.delete(article)
        db.session.commit()
        response = create_response(success=True, message='Article deleted successfully')
        return jsonify(response), 200
    else:
        response = create_response(error='Article not found')
        return jsonify(response), 404





