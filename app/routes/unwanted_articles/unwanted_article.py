from math import ceil
from sqlalchemy import desc, or_
from config import UnwantedArticle, db
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis

unwanted_articles_bp = Blueprint(
    'unwanted_articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@unwanted_articles_bp.route('/articles/unwanted', methods=['GET'])
@cache_with_redis()
@handle_db_session
def get_unwanted_articles():
    """
    Retrieves unwanted articles from the database with optional filtering, pagination, and search functionality.
    
    Query Parameters:
    - bot_id (int): Bot ID to filter unwanted articles (optional).
    - page (int): Page number (optional).
    - per_page (int): Number of items per page (optional, max: 100).
    - search (str): Search term to filter unwanted articles by title or content (optional).
    
    Returns:
        JSON: Response with unwanted article data, pagination info (if applicable), or error message.
    """
    try:
        bot_id = request.args.get('bot_id', type=int)
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)
        search_term = request.args.get('search', '')
        
        query = UnwantedArticle.query
        
        if bot_id:
            query = query.filter_by(bot_id=bot_id)
        
        if search_term:
            query = query.filter(or_(
                UnwantedArticle.title.ilike(f'%{search_term}%'),
                UnwantedArticle.content.ilike(f'%{search_term}%')
            ))
        
        query = query.order_by(desc(UnwantedArticle.created_at))
        
        total_items = query.count()
        
        if page is not None and per_page is not None:
            per_page = min(per_page, 100)
            if page < 1 or per_page < 1:
                return jsonify(create_response(error='Page and per_page must be positive integers')), 400
            
            total_pages = ceil(total_items / per_page)
            if page > total_pages and total_items > 0:
                return jsonify(create_response(error=f'Page {page} does not exist. Max page is {total_pages}')), 404
            
            unwanted_articles = query.paginate(page=page, per_page=per_page, error_out=False).items
            pagination_info = {
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_items': total_items
            }
        else:
            unwanted_articles = query.all()
            pagination_info = None
        
        if not unwanted_articles:
            message = 'No unwanted articles found for the specified criteria'
            return jsonify(create_response(success=True, data=[], message=message)), 204
        
        unwanted_article_data = [article.as_dict() for article in unwanted_articles]
        
        response = create_response(
            success=True,
            data=unwanted_article_data,
            message='Unwanted articles retrieved successfully',
            pagination=pagination_info
        )
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

