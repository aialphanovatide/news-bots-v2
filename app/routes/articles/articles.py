import os
from flask import Blueprint, json, jsonify, request
from app.services.perplexity.perplexity import perplexity_api_request
from app.utils.analyze_links import clean_text
from config import Article, db
from datetime import datetime
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.d3.dalle3 import generate_poster_prompt
import boto3
import requests
import pyperclip
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import re


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
        data = request.get_json()
        print("data", data)
        print("data", data['is_article_efficient'])

        # Validate required fields
        required_fields = ['title', 'content', 'analysis', 'used_keywords',
                           'is_article_efficient', 'bot_id', 'category_id', 'image_url']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            print(response['error'])
            return jsonify(response), 400

        # Download the generated image from DALL·E 3
        image_url = data['image_url']  # Ensure this key matches your incoming data
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            response['error'] = 'Failed to download image from DALL·E 3'
            print(response['error'])
            return jsonify(response), 500
        else:
            print("Image downloaded successfully")

        # Connect to AWS S3
        s3 = boto3.client(
            's3',
            region_name='us-east-2',  # AWS region
            aws_access_key_id=AWS_ACCESS,
            aws_secret_access_key=AWS_SECRET_KEY
        )

        image_data = image_response.content
        target_size = (512, 512)
        image_filename = f'{data["title"].replace(" ", "_")}.png'
        s3_bucket_name = 'sitesnewsposters'  # Your S3 bucket name
        app_bucket_name = 'appnewsposters'

        image = Image.open(BytesIO(image_data))

        # Upload original image to the specified S3 bucket
        try:
            s3.upload_fileobj(BytesIO(image_data), s3_bucket_name, image_filename)
            print("Image uploaded successfully to sitesnewsposters S3 bucket.")
        except Exception as e:
            response['error'] = f'Failed to upload image to S3: {str(e)}'
            print(response['error'])
            return jsonify(response), 500

        # Resize and upload to the app bucket
        resized_image = image.resize(target_size)
        with BytesIO() as output:
            resized_image.save(output, format="JPEG")
            output.seek(0)
            try:
                s3.upload_fileobj(output, app_bucket_name, image_filename)
                print("Image resized and uploaded successfully to appnewsposters S3 bucket.")
            except Exception as e:
                response['error'] = f'Failed to upload resized image to S3: {str(e)}'
                print(response['error'])
                return jsonify(response), 500

        # Construct the full URL of the image in S3
        image_url_s3 = f'https://{s3_bucket_name}.s3.us-east-2.amazonaws.com/{image_filename}'
        print("Image to save: ", image_url_s3)

        # Create a new article object
        current_time = datetime.now()
        new_article = Article(
            title=data['title'],
            content=data['content'].replace("- ", ""),
            image=image_url_s3,  # Use the S3 URL of the image
            analysis=data['analysis'],
            url="Generated By Ai-Alpha Team.",
            date=current_time,  # Current timestamp
            used_keywords=data['used_keywords'],
            is_article_efficent='Green ' + data['is_article_efficient'],
            is_top_story=False,
            bot_id=data['bot_id'],
            created_at=current_time,  # Current timestamp
            updated_at=current_time  # Current timestamp
        )

        # Save the new article to the database
        db.session.add(new_article)
        db.session.commit()

        # Prepare response with only necessary data
        response['data'] = new_article.as_dict()
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        # Rollback the database session in case of error
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


@articles_bp.route('/generate_article', methods=['POST'])
def generate_article():
    response = {'data': None, 'error': None, 'success': False}

    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['content', 'category_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {
                ", ".join(missing_fields)}'
            return jsonify(response), 400

        # Generate article summary using perplexity model
        perplexity_result = article_perplexity_remaker(
            data['content'], data['category_id'])
        if not perplexity_result['success']:
            response['error'] = perplexity_result['error']
            return jsonify(response), 400

        new_article_summary = perplexity_result['response']

        # Clean and process the article summary
        final_summary = clean_text(new_article_summary)
        final_summary = '\n'.join(line.lstrip('- ').strip()
                                  for line in final_summary.split('\n'))

        # Extract title and content from the processed summary
        first_line_end = final_summary.find('\n')
        if first_line_end != -1:
            new_article_title = final_summary[:first_line_end].strip()
            final_summary = final_summary[first_line_end + 1:].strip()
        else:
            new_article_title = final_summary.strip()
            final_summary = ""
            
                # Extract title and content from the processed summary
        lines = final_summary.split('\n')
        if lines:
            new_article_title = lines[0].strip()  # Use the first line as the title
            final_summary = '\n'.join(lines[1:]).strip()  # Join remaining lines as content

        final_title=new_article_title.replace("Headline: ", "")
        
        # Prepare response data with title and content
        response['data'] = {
            'title': final_title,
            'content': final_summary
        }

        print("title and content: ", final_title, final_summary)
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        # Handle exceptions and return error response
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500


@articles_bp.route('/generate_image', methods=['POST'])
def generate_image():
    response = {'data': None, 'error': None, 'success': False}

    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['content', 'bot_id']
        missing_fields = [
            field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {
                ", ".join(missing_fields)}'
            return jsonify(response), 400

        # Clean the content to get a final summary
        final_summary = clean_text(data['content'])

        # Extract the title from the cleaned summary
        first_line_end = final_summary.find('\n')
        if first_line_end != -1:
            new_article_title = final_summary[:first_line_end].strip()
        else:
            new_article_title = final_summary.strip()

        # Call function to generate poster prompt using DALL-E API
        dalle3_result = generate_poster_prompt(final_summary, data['bot_id'])
        if not dalle3_result['success']:
            response['error'] = dalle3_result['error']
            return jsonify(response), 400

        # Retrieve the original image URL provided by DALL-E
        original_image_url = dalle3_result['response']

        # Prepare response with original image URL
        response['data'] = {'image_url': original_image_url}
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        # Handle any internal server errors
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500



def extract_text_from_google_docs(link):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=2000)
            context = browser.new_context()
            page = context.new_page()
            page.goto(link)
            page.wait_for_load_state("domcontentloaded", timeout=70000)
            
            # Seleccionar todo el contenido del documento
            if os.name == 'posix':  # macOS o Linux
                page.keyboard.press('Meta+A')
                page.keyboard.press('Meta+C')
            else:  # Windows
                page.keyboard.press('Control+A')
                page.keyboard.press('Control+C')
            
            # Esperar un poco para asegurarse de que el contenido se copie
            page.wait_for_timeout(2000)
            
            # Obtener el contenido del portapapeles
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
    try:
        data = request.json
        extract_type = data.get('extract_type')
        content = data.get('content')
        link = data.get('link')

        if extract_type == 'link':
            prompt = "You are an assistant to create a summary about news"
            content = f" Please go to {link} and scrape the article text from the news/article"
            result = perplexity_api_request(content, prompt)
            print("result",result)

            if 'response' in result and isinstance(result['response'], str):
                response_text = result['response']
                if response_text:
                    cleaned_response = clean_response(response_text)
                    result['response'] = cleaned_response
                    print("cleaned_response: ", cleaned_response)
        elif extract_type == 'google_docs':
            content = extract_text_from_google_docs(link)
            result = {'response': content, 'success': True}
            print("content: ", content)
        else:
            return jsonify({'response': 'Invalid extract type', 'success': False})

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'response': f'An error occurred: {str(e)}', 'success': False}), 500

