from flask import Blueprint, jsonify, request
from config import Article, db
from datetime import datetime

articles_bp = Blueprint(
    'articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get all articles
@articles_bp.route('/get_all_articles', methods=['GET'])
def get_all_articles():

    response = {'data': None, 'error': None, 'success': False}
    try:
        limit = request.args.get('limit', default=10, type=int)
        if limit < 1:
            response['error'] = 'Limit must be a positive integer'
            return jsonify(response), 400

        articles = Article.query.limit(limit).all()
        if not articles:
            response['message'] = 'No articles found'
            response['success'] = True
            return jsonify(response), 200

        response['data'] = [article.as_dict() for article in articles]
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@articles_bp.route('/get_article_by_id/<int:article_id>', methods=['GET'])
def get_article_by_id(article_id):
    response = {'data': None, 'error': None, 'success': False}
    try:
        article = Article.query.filter_by(id=article_id).first()
        
        if not article:
            response['error'] = 'No article found for the specified article ID'
            return jsonify(response), 404

        response['data'] = article.as_dict()  
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


# Get all articles of a Bot
@articles_bp.route('/get_articles', methods=['GET'])
def get_articles_by_bot():

    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')
        limit = int(request.args.get('limit', 10))

        if not bot_id:
            response['error'] = 'Missing bot ID in request data'
            return jsonify(response), 400

        articles = Article.query.filter_by(bot_id=bot_id).limit(limit).all()
        if not articles:
            response['error'] = 'No articles found for the specified bot ID'
            return jsonify(response), 404

        response['data'] = [article.as_dict() for article in articles]
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500



# Delete an article by ID
@articles_bp.route('/delete_article', methods=['DELETE'])
def delete_article():

    response = {'data': None, 'error': None, 'success': False}
    try:
        # Get article ID from query arguments
        article_id = request.args.get('article_id')

        if not article_id:
            response['error'] = 'Article ID missing in request data'
            return jsonify(response), 400

        article = Article.query.get(article_id)
        if article:
            db.session.delete(article)
            db.session.commit()
            response['success'] = True
            response['message'] = 'Article deleted successfully'
            return jsonify(response), 200
        else:
            response['error'] = 'Article not found'
            return jsonify(response), 404
    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

