from flask import Blueprint, jsonify, request
from config import Article, db

articles_bp = Blueprint(
    'articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)
@articles_bp.route('/get_all_articles', methods=['GET'])
def get_all_articles():
    try:
        limit = int(request.args.get('limit', 10)) 
        articles = Article.query.limit(limit).all()  
        article_data = []
        for article in articles:
            article_data.append({
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'analysis': article.analysis,
                'url': article.url,
                'date': article.date,
                'used_keywords': article.used_keywords,
                'is_article_efficent': article.is_article_efficent,
                'bot_id': article.bot_id,
                'created_at': article.created_at,
                'updated_at': article.updated_at
            })
        return jsonify({'message': article_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articles_bp.route('/get_articles_by_bot', methods=['POST'])
def get_articles_by_bot(): 
    try:
        data = request.json
        bot_id = data.get('bot_id')
        limit = int(data.get('limit', 10)) 

        if bot_id is None:
            return jsonify({'error': 'Missing bot ID in request data'}), 400

        articles = Article.query.filter_by(bot_id=bot_id).limit(limit).all() 
        if not articles:
            return jsonify({'message': 'No articles found for the specified bot ID'}), 404

        article_data = []
        for article in articles:
            article_data.append({
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'analysis': article.analysis,
                'url': article.url,
                'date': article.date,
                'used_keywords': article.used_keywords,
                'is_article_efficent': article.is_article_efficent,
                'bot_id': article.bot_id,
                'created_at': article.created_at,
                'updated_at': article.updated_at
            })
        return jsonify({'message': article_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ESTA RUTA NO ES NECESARIA
@articles_bp.route('/create_article', methods=['POST'])
def create_article():
    try:
        data = request.json
        new_article = Article(
            title=data.get('title'),
            content=data.get('content'),
            analysis=data.get('analysis'),
            url=data.get('url'),
            date=data.get('date'),
            used_keywords=data.get('used_keywords'),
            is_article_efficent=data.get('is_article_efficent'),
            bot_id=data.get('bot_id')
        )
        db.session.add(new_article)
        db.session.commit()
        return jsonify({'message': 'Article created successfully', 'article_id': new_article.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@articles_bp.route('/delete_article', methods=['DELETE'])
def delete_article():
    try:
        data = request.json
        article_id = data.get('article_id')
        if article_id is None:
            return jsonify({'error': 'Article ID missing in request data'}), 400

        article = Article.query.get(article_id)
        if article:
            db.session.delete(article)
            db.session.commit()
            return jsonify({'message': 'Article deleted successfully'}), 200
        else:
            return jsonify({'error': 'Article not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
