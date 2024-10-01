from math import ceil
from sqlalchemy import desc
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


@unwanted_articles_bp.route('/unwanted-articles', methods=['GET'])
@cache_with_redis()
@handle_db_session
def get_unwanted_articles_by_bot():
    """
    Retrieves unwanted articles filtered by bot_id from the database with pagination.

    Query Parameters:
    - bot_id (str): Bot ID to filter unwanted articles (optional).
    - page (int): Page number (default: 1).
    - per_page (int): Number of items per page (default: 20, max: 100).

    Returns:
        JSON: Response with unwanted article data, pagination info, or error message.
    """
    try:
        bot_id = request.args.get('bot_id')
        page = request.args.get('page', default=1, type=int)
        per_page = min(request.args.get('per_page', default=20, type=int), 100)

        if page < 1 or per_page < 1:
            return jsonify(create_response(error='Page and per_page must be positive integers')), 400

        query = UnwantedArticle.query

        if bot_id:
            query = query.filter_by(bot_id=bot_id)

        total_items = query.count()
        total_pages = ceil(total_items / per_page)

        if page > total_pages and total_items > 0:
            return jsonify(create_response(error=f'Page {page} does not exist. Max page is {total_pages}')), 404

        unwanted_articles = query.order_by(desc(UnwantedArticle.created_at)).paginate(page=page, per_page=per_page, error_out=False)

        if not unwanted_articles.items:
            message = f'No unwanted articles found for the specified bot ID: {bot_id}' if bot_id else 'No unwanted articles found'
            return jsonify(create_response(success=True, data=[], message=message)), 204

        unwanted_article_data = [article.as_dict() for article in unwanted_articles.items]

        response = create_response(
            success=True,
            data=unwanted_article_data,
            message='Unwanted articles retrieved successfully',
            pagination={
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_items': total_items
            }
        )
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

