# routes.py

from datetime import datetime
import json
import os
from flask import Blueprint, jsonify, request
import requests
from app.routes.categories.utils import get_s3_url, upload_file_to_s3
from config import Article, Blacklist, Bot, Category, Keyword, Site, UnwantedArticle, UsedKeywords, db
from dotenv import load_dotenv
import boto3
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from dotenv import load_dotenv
import os

load_dotenv()

SERVER_LINK = os.getenv('SERVER_LINK')
load_dotenv()

OPENAI_APIKEY = os.getenv('OPENAI_APIKEY')
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

s3 = boto3.client(
    's3',
    region_name='us-east-2',
    aws_access_key_id=AWS_ACCESS,
    aws_secret_access_key=AWS_SECRET_KEY
)
@categories_bp.route('/add_new_category', methods=['POST'])
@handle_db_session
def create_category():
    """
    Create a new category.
    Data:
    Form data with 'name' (str), 'alias' (str), 'prompt' (str),
    'slack_channel' (str), optional 'is_active' (bool), 'border_color' (str), and an optional image file.
    Response:
    201: Category created successfully.
    400: Missing required fields or invalid request.
    500: Internal server error or database error.
    """
    try:
        data = json.loads(request.form.get('data'))
        # Input validation for required fields
        required_fields = ['name', 'alias', 'prompt', 'time_interval', 'slack_channel']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_response(error=f'Missing required fields: {", ".join(missing_fields)}')), 400

        existing_category = Category.query.filter_by(name=str(data['name']).casefold()).first()
        if existing_category:
            return jsonify(create_response(error=f'Category {data["name"]} already exists')), 400

        # Upload the image to S3
        image_url = None
        if 'image' in request.files:
            image_file = request.files['image']
            image_filename = f'{data["alias"]}.svg'
            if upload_file_to_s3(
                image_file,
                'aialphaicons',
                image_filename,
                extra_args={"ContentType": "image/svg+xml"}
            ):
                image_url = get_s3_url('aialphaicons', image_filename)

        # Create a new category
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            slack_channel=data['slack_channel'],
            prompt=data.get('prompt', ''),
            is_active=data.get('is_active', False),
            border_color=data.get('border_color', None),
            icon=image_url,
            created_at=datetime.now(),
        )
        db.session.add(new_category)
        db.session.commit()

        # Prepare the response with only necessary data
        return jsonify(create_response(success=True, data=new_category.as_dict())), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@handle_db_session
def delete_category(category_id):
    """
    Delete a single category by its ID and all related entries.
    Args:
    category_id (int): ID of the category to delete.
    Response:
    200: Category and related entries deleted successfully.
    404: Category not found.
    500: Internal server error or database error.
    """
    try:
        # Fetch the category to delete
        category = Category.query.get(category_id)
        if not category:
            return jsonify(create_response(error=f'Category with ID {category_id} not found')), 404

        # Delete the category (this will trigger cascading deletes)
        db.session.delete(category)

        # Commit the transaction
        db.session.commit()

        return jsonify(create_response(success=True, data={'deleted_id': category_id})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@categories_bp.route('/categories', methods=['GET'])
@handle_db_session
def get_categories():
    """
    Get all available categories along with their associated bots and bot details.
    Response:
    200: Successfully retrieved categories with their bots.
    404: No categories found.
    500: Internal server error or database error.
    """
    try:
        categories = Category.query.options(db.joinedload(Category.bots)).all()
        
        if not categories:
            return jsonify(create_response(error='No categories found')), 404
        
        categories_with_bots = []
        for category in categories:
            category_dict = category.as_dict()
            category_dict['bots'] = [bot.as_dict() for bot in category.bots]
            
            # Agregar detalles adicionales de los bots que no están en as_dict()
            for bot_dict, bot in zip(category_dict['bots'], category.bots):
                bot_dict.update({
                    'sites': [site.as_dict() for site in bot.sites],
                    'keywords': [keyword.as_dict() for keyword in bot.keywords],
                    'blacklist': [blacklist.as_dict() for blacklist in bot.blacklist],
                    'articles': [article.as_dict() for article in bot.articles],
                    'unwanted_articles': [unwanted_article.as_dict() for unwanted_article in bot.unwanted_articles],
                })
            
            categories_with_bots.append(category_dict)
        
        return jsonify(create_response(success=True, data={'categories': categories_with_bots})), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500
    
    
@categories_bp.route('/get_all_bots', methods=['GET'])
@handle_db_session
def get_bots():
    """
    Get all bots.
    Response:
        200: Successfully retrieved bots.
        500: Internal server error or database error.
    """
    try:
        categories = Category.query.order_by(Category.id).all()

        bots = [
            {
                'category': category.name,
                'isActive': category.is_active,
                'alias': category.alias,
                'icon': category.icon,
                'updated_at': category.updated_at,
                'color': category.border_color
            } for category in categories
        ]
        return jsonify(create_response(success=True, data={'bots': bots})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500



@categories_bp.route('/update_category/<int:category_id>', methods=['PUT'])
@handle_db_session
def update_category(category_id):
    """
    Update an existing category by ID.
    Args:
        category_id (int): ID of the category to update.
    Data:
        JSON with optional fields to update (name, alias, prompt, slack_channel, icon, time_interval, is_active, border_color).
    Response:
        200: Category updated successfully.
        400: Invalid request data or missing fields.
        404: Category not found.
        500: Internal server error or database error.
    """
    try:
        data = request.get_json()

        # Fetch the category to update
        category = Category.query.get(category_id)
        if not category:
            return jsonify(create_response(error=f'Category with ID {category_id} not found')), 404

        # Deactivate the category by calling the external route
        response = requests.post(
            f'{SERVER_LINK}/deactivate_category',
            json={'category_name': category.name}
        )
        if response.status_code != 200:
            return jsonify(create_response(error=f'Failed to deactivate category: {response.json().get("error")}')), 500

        # Update category fields
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)

        # Commit the changes to the category
        db.session.commit()

        # Reactivate the category by calling the external route
        response = requests.post(
            f'{SERVER_LINK}/activate_category',
            json={'category_name': category.name}
        )
        if response.status_code != 200:
            return jsonify(create_response(error=f'Failed to activate category: {response.json().get("error")}')), 500

        return jsonify(create_response(success=True, data=category.as_dict())), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500