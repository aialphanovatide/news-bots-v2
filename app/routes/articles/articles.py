import os
import re
from flask import Blueprint, json, jsonify, request
from app.utils.analyze_links import clean_text
from config import Article, db
from datetime import datetime
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.d3.dalle3 import generate_poster_prompt
import boto3
import requests
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

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
    


@articles_bp.route('/add_new_article', methods=['POST'])
def create_article():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.get_json()  # Obtener los datos directamente del cuerpo de la solicitud
        
        # Validación de campos requeridos
        required_fields = ['title', 'content', 'analysis', 'used_keywords', 'is_article_efficent', 'bot_id', 'category_id', 'image']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            print(response['error'])
            return jsonify(response), 400

        # Descargar la imagen generada desde DALL·E 3
        image_url = data['image']
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            response['error'] = 'Failed to download image from DALL·E 3'
            print(response['error'])
            return jsonify(response), 500

        image_data = image_response.content

        # Subir la imagen generada a S3
        image_filename = f'{data["title"].replace(" ", "_")}.png'  # Nombre de archivo basado en el título del artículo
        s3_bucket_name = 'sitesnewsposters'  # Nombre de tu bucket S3

        # connection to AWS
        s3 = boto3.client(
            's3',
            region_name='us-east-2',
            aws_access_key_id=AWS_ACCESS,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        try:
            s3.upload_fileobj(BytesIO(image_data), s3_bucket_name, image_filename)
        except Exception as e:
            response['error'] = f'Failed to upload image to S3: {str(e)}'
            print(response['error'])
            return jsonify(response), 500

        # Construir la URL completa de la imagen en S3
        image_url_s3 = f'https://{s3_bucket_name}.s3.us-east-2.amazonaws.com/{image_filename}'

        # Crear un nuevo artículo
        current_time = datetime.now()
        new_article = Article(
            title=data['title'],
            content=data['content'].replace("- ", ""),
            image=image_url_s3,  # Usar la URL de la imagen en S3
            analysis=data['analysis'],
            url="Generated By Ai-Alpha Team.",
            date=current_time,  # Usar la hora actual
            used_keywords=data['used_keywords'],
            is_article_efficent='Green ' + data['is_article_efficent'],
            is_top_story=False,
            bot_id=data['bot_id'],
            created_at=current_time,  # Usar la hora actual
            updated_at=current_time  # Usar la hora actual
        )

        db.session.add(new_article)
        db.session.commit()

        # Preparar la respuesta con solo los datos necesarios
        response['data'] = new_article.as_dict()
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500


@articles_bp.route('/generate_article', methods=['POST'])
def generate_article():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.get_json()
        required_fields = ['content', 'category_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify(response), 400

        perplexity_result = article_perplexity_remaker(data['content'], data['category_id'])
        if not perplexity_result['success']:
            response['error'] = perplexity_result['error']
            return jsonify(response), 400

        new_article_summary = perplexity_result['response']
        final_summary = clean_text(new_article_summary)
        
        final_summary = '\n'.join(line.lstrip('- ').strip() for line in final_summary.split('\n'))
        
        first_line_end = final_summary.find('\n')
        if first_line_end != -1:
            new_article_title = final_summary[:first_line_end].strip()
            final_summary = final_summary[first_line_end + 1:].strip()
        else:
            new_article_title = final_summary.strip()
            final_summary = ""

        response['data'] = {
            'title': new_article_title,
            'content': final_summary
        }
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500


@articles_bp.route('/generate_image', methods=['POST'])
def generate_image():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.get_json()
        required_fields = ['content', 'bot_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify(response), 400

        final_summary = clean_text(data['content'])
        first_line_end = final_summary.find('\n')
        if first_line_end != -1:
            new_article_title = final_summary[:first_line_end].strip()
        else:
            new_article_title = final_summary.strip()

        dalle3_result = generate_poster_prompt(final_summary, data['bot_id'])
        if not dalle3_result['success']:
            response['error'] = dalle3_result['error']
            return jsonify(response), 400

        # Devolver el enlace original de la imagen proporcionado por DALL-E
        original_image_url = dalle3_result['response']

        response['data'] = {'image_url': original_image_url}
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500
