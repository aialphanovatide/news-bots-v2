from flask import Blueprint, jsonify, request
from config import UnwantedArticle, db

unwanted_articles_bp = Blueprint(
    'unwanted_articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Ruta para obtener todos los UnwantedArticles filtrados por bot_id
@unwanted_articles_bp.route('/get_unwanted_articles_by_bot', methods=['POST'])
def get_unwanted_articles_by_bot():
    try:
        data = request.json
        bot_id = data.get('bot_id')

        if bot_id is None:
            return jsonify({'error': 'Bot ID missing in request data'}), 400

        unwanted_articles = UnwantedArticle.query.filter_by(bot_id=bot_id).all()

        if not unwanted_articles:
            return jsonify({'message': 'No unwanted articles found for the specified bot ID'}), 404

        unwanted_article_data = []
        for unwanted_article in unwanted_articles:
            unwanted_article_data.append({
                'id': unwanted_article.id,
                'title': unwanted_article.title,
                'content': unwanted_article.content,
                'analysis': unwanted_article.analysis,
                'url': unwanted_article.url,
                'date': unwanted_article.date,
                'used_keywords': unwanted_article.used_keywords,
                'is_article_efficent': unwanted_article.is_article_efficent,
                'bot_id': unwanted_article.bot_id,
            })

        return jsonify({'message': unwanted_article_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para agregar un nuevo UnwantedArticle
@unwanted_articles_bp.route('/add_unwanted_article', methods=['POST'])
def add_unwanted_article():
    try:
        data = request.json
        new_unwanted_article = UnwantedArticle(
            title=data['title'],
            content=data['content'],
            analysis=data['analysis'],
            url=data['url'],
            date=data['date'],
            used_keywords=data['used_keywords'],
            is_article_efficent=data['is_article_efficent'],
            bot_id=data['bot_id']
        )
        db.session.add(new_unwanted_article)
        db.session.commit()
        return jsonify({'message': 'Unwanted article added successfully', 'article_id': new_unwanted_article.id}), 200
    except KeyError as e:
        return jsonify({'error': f'Missing key in request data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


