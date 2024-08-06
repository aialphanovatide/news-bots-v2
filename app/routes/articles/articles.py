import os
from datetime import datetime
from io import BytesIO
import re
from flask import Blueprint, jsonify, request
from PIL import Image
from dotenv import load_dotenv
import boto3
import pyperclip
import requests
from app.routes.routes_utils import create_response, handle_db_session
from app.services.perplexity.perplexity import perplexity_api_request
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.utils.analyze_links import clean_text
from config import Article, Bot, Category, db
from app.services.d3.dalle3 import generate_poster_prompt
from sqlalchemy.exc import SQLAlchemyError
from playwright.sync_api import sync_playwright


load_dotenv()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

articles_bp = Blueprint('articles_bp', __name__, template_folder='templates', static_folder='static')

root_dir = os.path.abspath(os.path.dirname(__file__))
user_data_dir = os.path.join(root_dir, 'tmp/playwright')
os.makedirs(user_data_dir, exist_ok=True)


@articles_bp.route('/get_all_articles', methods=['GET'])
@handle_db_session
def get_all_articles():
    """
    Retrieve all articles with an optional limit.
    
    Returns:
        JSON response with the list of articles or an error message.
    """
    limit = request.args.get('limit', default=10, type=int)
    if limit < 1:
        response = create_response(error='Limit must be a positive integer')
        return jsonify(response), 400

    articles = Article.query.order_by(Article.created_at.desc()).limit(limit).all()
    if not articles:
        response = create_response(success=True, data=[], error='No articles found')
        return jsonify(response), 404

    response = create_response(success=True, data=[article.as_dict() for article in articles])
    return jsonify(response), 200



@articles_bp.route('/get_article_by_id/<int:article_id>', methods=['GET'])
@handle_db_session
def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID.
    
    Args:
        article_id (int): The ID of the article to retrieve.
    
    Returns:
        JSON response with the article data or an error message.
    """
    article = Article.query.filter_by(id=article_id).first()
    if not article:
        response = create_response(error='No article found for the specified article ID')
        return jsonify(response), 404

    response = create_response(success=True, data=article.as_dict())
    return jsonify(response), 200


@articles_bp.route('/get_articles', methods=['GET'])
@handle_db_session
def get_articles_by_bot():
    """
    Retrieve articles by bot ID or bot name with an optional limit.
    
    Returns:
        JSON response with the list of articles or an error message.
    """
    bot_id = request.args.get('bot_id')
    bot_name = request.args.get('bot_name')
    limit = request.args.get('limit', default=10, type=int)

    if not bot_id and not bot_name:
        response = create_response(error='Missing bot ID or bot name in request data')
        return jsonify(response), 400

    if bot_name:
        bot = Bot.query.filter_by(name=bot_name).first()
        if not bot:
            response = create_response(error='No bot found with the specified bot name')
            return jsonify(response), 404
        bot_id = bot.id

    articles = Article.query.filter_by(bot_id=bot_id).order_by(Article.created_at.desc()).limit(limit).all()
    if not articles:
        response = create_response(error='No articles found for the specified bot ID')
        return jsonify(response), 404

    response = create_response(success=True, data=[article.as_dict() for article in articles])
    return jsonify(response), 200



@articles_bp.route('/delete_article', methods=['DELETE'])
@handle_db_session
def delete_article():
    """
    Delete an article by its ID.
    
    Args:
        article_id (int): The ID of the article to delete.
    
    Returns:
        JSON response with the success status or an error message.
    """
    article_id = request.args.get('article_id')
    if not article_id:
        response = create_response(error='Article ID missing in request data')
        return jsonify(response), 400

    article = Article.query.get(article_id)
    if article:
        db.session.delete(article)
        db.session.commit()
        response = create_response(success=True, message='Article deleted successfully')
        return jsonify(response), 200
    else:
        response = create_response(error='Article not found')
        return jsonify(response), 404

@articles_bp.route('/add_new_article', methods=['POST'])
@handle_db_session
def create_article():
    """
    Create a new article with provided data.
    
    Returns:
        JSON response with the created article data or an error message.
    """
    data = request.get_json()

    # Validar campos obligatorios
    required_fields = ['title', 'content', 'analysis', 'used_keywords', 'is_article_efficient', 'bot_id', 'category_id', 'image_url']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        response = create_response(error=f'Missing required fields: {", ".join(missing_fields)}')
        return jsonify(response), 400
    
    image_url = data['image_url']
    try:
        # Descargar imagen
        image_response = requests.get(image_url)
        image_response.raise_for_status()  # Lanza excepción si la respuesta tiene un código de error
    except requests.exceptions.RequestException as e:
        response = create_response(error=f'Failed to download image from URL: {str(e)}')
        return jsonify(response), 500

    s3 = boto3.client('s3', region_name='us-east-2', aws_access_key_id=AWS_ACCESS, aws_secret_access_key=AWS_SECRET_KEY)
    image_data = image_response.content
    target_size = (512, 512)
    
    # Generar nombre del archivo
    image_filename = f'{data["title"].replace(" ", "_")}.png'
    image_filename = re.sub(r'[^a-zA-Z0-9_]', '', image_filename)
    image_filename = f"{image_filename}.jpg"
    
    s3_bucket_name = 'sitesnewsposters'
    app_bucket_name = 'appnewsposters'
    category_id = data["category_id"]
    
    try:
        # Subir imagen original a S3
        s3.upload_fileobj(BytesIO(image_data), s3_bucket_name, image_filename)
    except Exception as e:
        response = create_response(error=f'Failed to upload image to S3: {str(e)}')
        return jsonify(response), 500

    # Redimensionar imagen
    image = Image.open(BytesIO(image_data))
    resized_image = image.resize(target_size)
    
    with BytesIO() as output:
        try:
            resized_image.save(output, format="JPEG")
            output.seek(0)
            # Subir imagen redimensionada a S3
            s3.upload_fileobj(output, app_bucket_name, image_filename)
        except Exception as e:
            response = create_response(error=f'Failed to upload resized image to S3: {str(e)}')
            return jsonify(response), 500

    image_url_s3 = f'https://{s3_bucket_name}.s3.us-east-2.amazonaws.com/{image_filename}'
    current_time = datetime.now()

    try:
        new_article = Article(
            title=data['title'],
            content=data['content'].replace("- ", ""),
            image=image_filename,
            analysis=data['analysis'],
            url="Generated By Ai-Alpha Team.",
            date=current_time,
            used_keywords=data['used_keywords'],
            is_article_efficent='Green ' + data['is_article_efficient'],
            is_top_story=data.get('is_top_story', False), 
            bot_id=data['bot_id'],
            created_at=current_time,
            updated_at=current_time
        )

        db.session.add(new_article)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        response = create_response(error=f'Failed to save article to database: {str(e)}')
        return jsonify(response), 500

    # Buscar categoría y enviar notificación a Slack
    category = Category.query.filter_by(id=category_id).first()
    if category:
        channel_slack = category.slack_channel
        used_keywords_list = new_article.used_keywords if isinstance(new_article.used_keywords, list) else [new_article.used_keywords]

        response = send_NEWS_message_to_slack_channel(
            channel_id=channel_slack, 
            title=new_article.title,
            article_url="Generated By Ai-Alpha Team.",
            content=new_article.content, 
            used_keywords=used_keywords_list, 
            image=f'https://{s3_bucket_name}.s3.us-east-2.amazonaws.com/{new_article.image}'
        )
        
        print("Slack response:", response)
    else:
        response = create_response(error='Category not found')
        return jsonify(response), 400

    response = create_response(success=True, data=new_article.as_dict())
    return jsonify(response), 200


@articles_bp.route('/generate_image', methods=['POST'])
def generate_image():               
    """
    Generate an image using the DALL-E 3 model.
    """
    try:
        data = request.get_json()
        print(data)
        required_fields = ['content', 'bot_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response = create_response(error=f'Missing required fields: {", ".join(missing_fields)}')
            return jsonify(response), 400

        final_summary = clean_text(data['content'])

        dalle3_result = generate_poster_prompt(final_summary, data['bot_id'])
        if not dalle3_result['success']:
            response = create_response(error=dalle3_result['error'])
            return jsonify(response), 400

        original_image_url = dalle3_result['response']

        response = create_response(success=True, data={'image_url': original_image_url})
        return jsonify(response), 200

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@articles_bp.route('/generate_article', methods=['POST'])
@handle_db_session
def generate_article():
    """
    Generate a new article summary using the perplexity model.
    
    Returns:
        JSON response with the generated article summary or an error message.
    """
    data = request.get_json()
    required_fields = ['content', 'category_id']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        response = create_response(error=f'Missing required fields: {", ".join(missing_fields)}')
        return jsonify(response), 400
    
    try:
        article_content = clean_text(data['content'])
        article_summary = perplexity_api_request(content=article_content, prompt="you are a economic yournalist writing about crypto and other economics, generate an news article talking about this crypto content in less than 150 words: ")
        
        if not article_summary:
            response = create_response(error='Failed to generate article summary')
            return jsonify(response), 500
        
        response = create_response(success=True, data={'summary': article_summary})
        return jsonify(response), 200
    
    except Exception as e:
        response = create_response(error=str(e))
        return jsonify(response), 500


@articles_bp.route('/last_five_articles', methods=['GET'])
@handle_db_session
def get_last_five_articles():
    """
    Get the last five articles with extended details.
    Response:
        200: Successfully retrieved the last five articles.
        404: No articles found matching the criteria.
        500: Internal server error.
    """
    try:
        # Fetch the last five articles that match the given criteria
        articles = Article.query.filter_by(url="Generated By Ai-Alpha Team.") \
                                .order_by(Article.date.desc()) \
                                .limit(5) \
                                .all()

        if not articles:
            return create_response(error='No articles found matching the criteria', status=404)

        extended_articles = []
        for article in articles:
            bot = Bot.query.get(article.bot_id)
            bot_name = bot.name if bot else None

            category = Category.query.get(bot.category_id) if bot else None
            category_name = category.name if category else None

            extended_article = {
                'id': article.id,
                'title': article.title,
                'content': article.content,
                'image': article.image,
                'analysis': article.analysis,
                'bot_id': article.bot_id,
                'bot_name': bot_name,
                'category_name': category_name,
                'created_at': article.created_at.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'updated_at': article.updated_at.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'date': article.date.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                'url': article.url,
                'used_keywords': article.used_keywords,
                'is_article_efficent': article.is_article_efficent,
                'is_top_story': article.is_top_story
            }

            extended_articles.append(extended_article)

        return create_response(data=extended_articles, status=200)

    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}', status=500)
    except Exception as e:
        return create_response(error=f'Internal server error: {str(e)}', status=500)
    


def extract_text_from_google_docs(link):
    """
    Extract text content from a Google Docs link.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(link)
            page.wait_for_load_state("domcontentloaded", timeout=70000)

            if os.name == 'posix':  # macOS or Linux
                page.keyboard.press('Meta+A')
                page.keyboard.press('Meta+C')
            else:  # Windows
                page.keyboard.press('Control+A')
                page.keyboard.press('Control+C')

            page.wait_for_timeout(4000)
            content = pyperclip.paste()
            browser.close()
            return content
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def clean_response(response):
    """
    Erase the first and last lines from the response.
    """
    if response:
        lines = response.split('\n')
        if len(lines) > 2:
            return '\n'.join(lines[1:-1])
        else:
            return ''
    return response

@articles_bp.route('/extract_content', methods=['POST'])
def extract_content():
    """
    Extract content from a link or Google Docs based on the extract type.
    """
    response = {'response': None, 'success': False}
    try:
        data = request.get_json()
        extract_type = data.get('extract_type')
        link = data.get('link')

        if extract_type == 'link':
            prompt = "You are an assistant to create a summary about news"
            content = f"Please go to {link} and scrape the article text from the news/article"
            result = perplexity_api_request(content, prompt)

            if 'response' in result and isinstance(result['response'], str):
                response_text = result['response']
                if response_text:
                    cleaned_response = clean_response(response_text)
                    result['response'] = cleaned_response
        elif extract_type == 'google_docs':
            content = extract_text_from_google_docs(link)
            result = {'response': content, 'success': True}
        else:
            return jsonify({'response': 'Invalid extract type', 'success': False})

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'response': f'An error occurred: {str(e)}', 'success': False}), 500
    
@articles_bp.route('/api/update/top-story/<int:article_id>', methods=['PUT'])
def update_top_story(article_id):
    try:
        # Buscar el artículo en la tabla Article
        article = db.session.query(Article).filter(Article.id == article_id).first()

        if not article:
            return jsonify({'message': 'No article found'}), 404
        
        # Cambiar la columna is_top_story a False
        article.is_top_story = False
        db.session.commit()

        return jsonify({'message': 'Article updated to not be a top story'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred updating the article: {str(e)}'}), 500
