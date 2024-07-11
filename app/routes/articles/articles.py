import os
from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Article, Bot, db
from datetime import datetime
import boto3
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError


load_dotenv()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

articles_bp = Blueprint(
    'articles_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

root_dir = os.path.abspath(os.path.dirname(__file__))
user_data_dir = os.path.join(root_dir, 'tmp/playwright')

if not os.path.exists(user_data_dir):
    os.makedirs(user_data_dir, exist_ok=True)

@articles_bp.route('/get_all_articles', methods=['GET'])
@measure_execution_time
def get_all_articles():
    """
    Get all articles with a limit.
    Args:
        limit (int): The maximum number of articles to retrieve. Default is 10.
    Response:
        200: Successfully retrieved articles.
        400: Bad request if limit is invalid.
        500: Internal server error.
    """
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
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@articles_bp.route('/get_article_by_id/<int:article_id>', methods=['GET'])
@measure_execution_time
def get_article_by_id(article_id):
    """
    Get a single article by its ID.
    Args:
        article_id (int): The ID of the article to retrieve.
    Response:
        200: Successfully retrieved the article.
        404: Article not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        article = Article.query.filter_by(id=article_id).first()
        if not article:
            response['error'] = 'No article found for the specified article ID'
            return jsonify(response), 404

        response['data'] = article.as_dict()
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@articles_bp.route('/get_articles', methods=['GET'])
@measure_execution_time
def get_articles_by_bot():
    """
    Get articles associated with a specific bot.
    Args:
        bot_id (int): The ID of the bot.
        bot_name (str): The name of the bot.
        limit (int): The maximum number of articles to retrieve. Default is 10.
    Response:
        200: Successfully retrieved articles.
        400: Bad request if parameters are missing.
        404: Bot or articles not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')
        bot_name = request.args.get('bot_name')
        limit = int(request.args.get('limit', 10))

        if not bot_id and not bot_name:
            response['error'] = 'Missing bot ID or bot name in request data'
            return jsonify(response), 400

        if bot_name:
            bot = Bot.query.filter_by(name=bot_name).first()
            if not bot:
                response['error'] = 'No bot found with the specified bot name'
                return jsonify(response), 404
            bot_id = bot.id

        articles = Article.query.filter_by(bot_id=bot_id).limit(limit).all()
        if not articles:
            response['error'] = 'No articles found for the specified bot ID'
            return jsonify(response), 404

        response['data'] = [article.as_dict() for article in articles]
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@articles_bp.route('/delete_article', methods=['DELETE'])
def delete_article():
    """
    Delete an article by its ID.
    Args:
        article_id (int): The ID of the article to delete.
    Response:
        200: Successfully deleted the article.
        400: Bad request if article ID is missing.
        404: Article not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
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
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


#dashboard searchtool. 
@articles_bp.route('/get_last_articles', methods=['GET'])
def get_last_articles():
    response = {'data': None, 'error': None, 'success': False}
    try:
        limit = int(request.args.get('limit', 50))

        if limit < 1:
            response['error'] = 'Limit must be a positive integer'
            return jsonify(response), 400

        articles = Article.query.order_by(Article.date.desc()).limit(limit).all()
        if not articles:
            response['message'] = 'No articles found'
            response['success'] = True
            return jsonify(response), 200

        response['data'] = [article.as_dict() for article in articles]
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
@articles_bp.route('/add_new_article', methods=['POST'])
def create_article():
    """
    Create a new article.
    Args:
        title (str): Title of the article.
        content (str): Content of the article.
        analysis (str): Analysis of the article.
        used_keywords (list): List of used keywords.
        is_article_efficient (str): Efficiency of the article.
        bot_id (int): ID of the bot.
        category_id (int): ID of the category.
        image_url (str): URL of the image.
    Response:
        200: Successfully created the article.
        400: Bad request if required fields are missing or image download fails.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.get_json()
        required_fields = ['title', 'content', 'analysis', 'used_keywords', 'is_article_efficient', 'bot_id', 'category_id', 'image_url']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify(response), 400

        image_url = data['image_url']
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            response['error'] = 'Failed to download image from DALL·E 3'
            return jsonify(response), 500

        s3 = boto3.client('s3', region_name='us-east-2', aws_access_key_id=AWS_ACCESS, aws_secret_access_key=AWS_SECRET_KEY)
        image_data = image_response.content
        target_size = (512, 512)
        image_filename = f'{data["title"].replace(" ", "_")}.png'
        s3_bucket_name = 'sitesnewsposters'
        app_bucket_name = 'appnewsposters'

        image = Image.open(BytesIO(image_data))
        try:
            s3.upload_fileobj(BytesIO(image_data), s3_bucket_name, image_filename)
        except Exception as e:
            response['error'] = f'Failed to upload image to S3: {str(e)}'
            return jsonify(response), 500

        resized_image = image.resize(target_size)
        with BytesIO() as output:
            resized_image.save(output, format="JPEG")
            output.seek(0)
            try:
                s3.upload_fileobj(output, app_bucket_name, image_filename)
            except Exception as e:
                response['error'] = f'Failed to upload resized image to S3: {str(e)}'
                return jsonify(response), 500

        image_url_s3 = f'https://{s3_bucket_name}.s3.us-east-2.amazonaws.com/{image_filename}'
        current_time = datetime.now()
        new_article = Article(
            title=data['title'],
            content=data['content'].replace("- ", ""),
            image=image_url_s3,
            analysis=data['analysis'],
            url="Generated By Ai-Alpha Team.",
            date=current_time,
            used_keywords=data['used_keywords'],
            is_article_efficent='Green ' + data['is_article_efficient'],
            bot_id=data['bot_id'],
            category_id=data['category_id']
        )
        db.session.add(new_article)
        db.session.commit()

        response['data'] = new_article.as_dict()
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@articles_bp.route('/get_all_articles_title', methods=['GET'])
@measure_execution_time
def get_all_articles_title():
    """
    Get all article titles with a limit.
    Args:
        limit (int): The maximum number of article titles to retrieve. Default is 10.
    Response:
        200: Successfully retrieved article titles.
        400: Bad request if limit is invalid.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        limit = int(request.args.get('limit', 10))
        articles = Article.query.limit(limit).all()
        if not articles:
            response['message'] = 'No articles found'
            response['success'] = True
            return jsonify(response), 200

        response['data'] = [{'title': article.title} for article in articles]
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500
