from datetime import datetime
from flask import Blueprint, jsonify, request
from config import UnwantedArticle, db
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

unwanted_articles_bp = Blueprint(
    'unwanted_articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@unwanted_articles_bp.route('/get_unwanted_articles', methods=['GET'])
@handle_db_session
def get_unwanted_articles_by_bot():
    """
    Retrieves unwanted articles filtered by bot_id from the database.

    Args:
        bot_id (str): Bot ID to filter unwanted articles.

    Returns:
        JSON: Response with unwanted article data or error message.
    """
    try:
        bot_id = request.args.get('bot_id')
        limit = request.args.get('limit', default=200, type=int)

        if limit < 1:
            response = create_response(error='Limit must be a positive integer')
            return jsonify(response), 400

        query = UnwantedArticle.query

        if bot_id:
            query = query.filter_by(bot_id=bot_id)

        unwanted_articles = query.order_by(UnwantedArticle.created_at.desc()).limit(limit).all()

        if not unwanted_articles:
            response = create_response(
                error=f'No unwanted articles found for the specified bot ID: {bot_id}' if bot_id else 'No unwanted articles found'
            )
            return jsonify(response), 404

        unwanted_article_data = [article.as_dict() for article in unwanted_articles]

        response = create_response(success=True, data=unwanted_article_data, message='Unwanted articles retrieved successfully')
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@unwanted_articles_bp.route('/search_unwanted_articles', methods=['POST'])
@handle_db_session
def search_unwanted_articles():
    """
    Searches unwanted articles by title or content using a search query.

    Returns:
        JSON: Response with matching unwanted article data or error message.
    """
    try:
        search_query = request.json.get('search_query')

        if not search_query:
            response = create_response(error='Search query missing in request data')
            return jsonify(response), 400

        unwanted_articles = UnwantedArticle.query.filter(
            (UnwantedArticle.title.ilike(f'%{search_query}%')) |
            (UnwantedArticle.content.ilike(f'%{search_query}%'))
        ).all()

        if not unwanted_articles:
            response = create_response(error='No matching unwanted articles found for the specified search query')
            return jsonify(response), 404

        unwanted_article_data = [article.as_dict() for article in unwanted_articles]

        response = create_response(success=True, data=unwanted_article_data, message='Unwanted articles retrieved successfully')
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500
    
    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500
