from datetime import datetime
from flask import Blueprint, jsonify, request
from config import UnwantedArticle, db
from sqlalchemy.exc import SQLAlchemyError

unwanted_articles_bp = Blueprint(
    'unwanted_articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get unwanted articles by bot ID
@unwanted_articles_bp.route('/get_unwanted_articles', methods=['GET'])
def get_unwanted_articles_by_bot():
    """
    Retrieves unwanted articles filtered by bot_id from the database.

    Args:
        bot_id (str): Bot ID to filter unwanted articles.

    Returns:
        JSON: Response with unwanted article data or error message.
    """
    response = {'data': None, 'error': None, 'success': False, 'message': None}
    try:
        bot_id = request.args.get('bot_id')

        if bot_id:
            unwanted_articles = UnwantedArticle.query.filter_by(bot_id=bot_id).all()
        else:
            unwanted_articles = UnwantedArticle.query.all()

        if not unwanted_articles:
            response['error'] = 'No unwanted articles found' + (f' for the specified bot ID: {bot_id}' if bot_id else '')
            return jsonify(response), 404

        unwanted_article_data = [article.as_dict() for article in unwanted_articles]

        response['data'] = unwanted_article_data
        response['success'] = True
        response['message'] = 'Unwanted articles retrieved successfully'
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
        return jsonify(response), 500
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


# Search for unwanted articles by search query
@unwanted_articles_bp.route('/search_unwanted_articles', methods=['POST'])
def search_unwanted_articles():
    """
    Searches unwanted articles by title or content using a search query.

    Returns:
        JSON: Response with matching unwanted article data or error message.
    """
    response = {'data': None, 'error': None, 'success': False, 'message': None}
    try:
        search_query = request.json.get('search_query')

        if not search_query:
            response['error'] = 'Search query missing in request data'
            return jsonify(response), 400

        unwanted_articles = UnwantedArticle.query.filter(
            (UnwantedArticle.title.ilike(f'%{search_query}%')) |
            (UnwantedArticle.content.ilike(f'%{search_query}%'))
        ).all()

        if not unwanted_articles:
            response['error'] = 'No matching unwanted articles found for the specified search query'
            return jsonify(response), 404

        unwanted_article_data = [article.as_dict() for article in unwanted_articles]

        response['data'] = unwanted_article_data
        response['success'] = True
        response['message'] = 'Unwanted articles retrieved successfully'
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
        return jsonify(response), 500
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500
