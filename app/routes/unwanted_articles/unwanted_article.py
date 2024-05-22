from datetime import datetime
from flask import Blueprint, jsonify, request
from config import UnwantedArticle, db

unwanted_articles_bp = Blueprint(
    'unwanted_articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get unwanted articles by bot ID
@unwanted_articles_bp.route('/get_unwanted_articles', methods=['GET'])
def get_unwanted_articles_by_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')

        if not bot_id:
            response['error'] = 'Bot ID missing in request data'
            return jsonify(response), 400

        unwanted_articles = UnwantedArticle.query.filter_by(bot_id=bot_id).all()

        if not unwanted_articles:
            response['error'] = 'No unwanted articles found for the specified bot ID'
            return jsonify(response), 404

        unwanted_article_data = [article.as_dict() for article in unwanted_articles]

        response['data'] = unwanted_article_data
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500



# Search for unwanted articles by search query
@unwanted_articles_bp.route('/search_unwanted_articles', methods=['POST'])
def search_unwanted_articles():
    response = {'data': None, 'error': None, 'success': False}
    try:
        search_query = request.args.get('search_query')

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
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

    

