
from math import ceil
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from config import Article, Bot, db, UnwantedArticle
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis, update_cache_with_redis

articles_bp = Blueprint('articles_bp', __name__, 
                        template_folder='templates', 
                        static_folder='static')

@articles_bp.route('/articles', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_all_articles():
    """
    Retrieve articles with optional pagination.
    
    Query Parameters:
    - page: The page number (optional)
    - per_page: Number of articles per page (optional)
    
    Returns:
        JSON response with the list of articles, pagination info (if applicable), or an error message.
    """
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', type=int)

    if (page is not None and page < 1) or (per_page is not None and per_page < 1):
        response = create_response(error='Page and per_page must be positive integers')
        return jsonify(response), 400

    query = Article.query.order_by(desc(Article.created_at))
    total_articles = query.count()

    if page is None or per_page is None:
        articles = query.all()
        pagination_info = None
    else:
        total_pages = ceil(total_articles / per_page)
        if page > total_pages and total_articles > 0:
            response = create_response(error=f'Page {page} does not exist. Max page is {total_pages}')
            return jsonify(response), 404

        articles = query.paginate(page=page, per_page=per_page, error_out=False).items
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_articles
        }

    if not articles:
        response = create_response(success=True, data=[], message='No articles found')
        return jsonify(response), 204

    response = create_response(
        success=True,
        data=[article.as_dict() for article in articles],
        pagination=pagination_info
    )
    return jsonify(response), 200


@articles_bp.route('/article/<int:article_id>', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID from either the Article or UnwantedArticle table.
    
    This function queries the database for an article with the specified ID in both the Article
    and UnwantedArticle tables. It returns the article details if found in either table.
    If the article is not found in either table, it returns an error response.
    
    Args:
        article_id (int): The ID of the article to retrieve.
    
    Returns:
        JSON response with the article data or an error message.
    """
    article = Article.query.filter_by(id=article_id).first()
    
    if article:
        response = create_response(success=True, data=article.as_dict(), source="Article")
        return jsonify(response), 200
    
    unwanted_article = UnwantedArticle.query.filter_by(id=article_id).first()
    
    if unwanted_article:
        response = create_response(success=True, data=unwanted_article.as_dict(), source="UnwantedArticle")
        return jsonify(response), 200
    
    response = create_response(error='No article found for the specified article ID in either Article or UnwantedArticle table')
    return jsonify(response), 404


@articles_bp.route('/article', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_articles_by_bot():
    """
    Retrieve articles by bot ID or bot name with optional pagination and search functionality.
    
    Query Parameters:
    - bot_id: ID of the bot (optional if bot_name is provided)
    - bot_name: Name of the bot (optional if bot_id is provided)
    - page: The page number (optional)
    - per_page: Number of articles per page (optional)
    - search: Search term to filter articles by content (optional)
    
    Returns:
        JSON response with the list of articles, pagination info (if applicable), or an error message.
    """
    bot_id = request.args.get('bot_id', type=int)
    bot_name = request.args.get('bot_name')
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', type=int)
    search_term = request.args.get('search', '')

    if not bot_id and not bot_name:
        return jsonify(create_response(error='Missing bot ID or bot name in request data')), 400

    if bot_name:
        bot = Bot.query.filter_by(name=bot_name).first()
        if not bot:
            return jsonify(create_response(error='No bot found with the specified bot name')), 404
        bot_id = bot.id

    if (page is not None and page < 1) or (per_page is not None and per_page < 1):
        return jsonify(create_response(error='Page and per_page must be positive integers')), 400

    query = Article.query.filter_by(bot_id=bot_id)

    if search_term:
        query = query.filter(Article.content.ilike(f'%{search_term}%'))

    query = query.order_by(desc(Article.created_at))
    
    total_articles = query.count()

    if page is None or per_page is None:
        articles = query.all()
        pagination_info = None
    else:
        total_pages = ceil(total_articles / per_page)
        if page > total_pages and total_articles > 0:
            return jsonify(create_response(error=f'Page {page} does not exist. Max page is {total_pages}')), 404

        articles = query.paginate(page=page, per_page=per_page, error_out=False).items
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_articles
        }

    if not articles:
        return jsonify(create_response(success=True, data=[], message='No articles found for the specified criteria')), 204

    response = create_response(
        success=True,
        data=[article.as_dict() for article in articles],
        pagination=pagination_info
    )
    return jsonify(response), 200



@articles_bp.route('/article/<int:article_id>', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_all_articles', 'get_article_by_id', 'get_articles_by_bot'])
@handle_db_session
def delete_article(article_id):
    """
    Delete an article by its ID.
    
    Args:
        article_id (int): The ID of the article to delete.
    
    Returns:
        JSON response with the success status or an error message.
    """
    if not article_id:
        return jsonify(create_response(error='Article ID is required')), 400

    try:
        article = Article.query.get(article_id)
        if not article:
            return jsonify(create_response(error='Article not found')), 404

        db.session.delete(article)
        db.session.commit()
        return jsonify(create_response(success=True, message='Article deleted successfully')), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500





