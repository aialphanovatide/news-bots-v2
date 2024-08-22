# routes.py

from datetime import datetime
import json
import os
from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Category, db
from dotenv import load_dotenv
import boto3
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
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
@measure_execution_time
@handle_db_session
def create_category():
    """
    Create a new category.
    Data:
        Form data with 'name' (str), 'alias' (str), 'prompt' (str), 'time_interval' (int),
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

        # Check if the category already exists
        existing_category = Category.query.filter_by(name=str(data['name']).casefold()).first()
        if existing_category:
            return jsonify(create_response(error=f'Category {data["name"]} already exists')), 400

        # Upload the image to S3
        if 'image' in request.files:
            image_file = request.files['image']
            image_filename = f'{data["alias"]}.png'
            s3.upload_fileobj(image_file, 'aialphaicons', image_filename)
            image_url = f'https://aialphaicons.s3.amazonaws.com/{image_filename}'
        else:
            image_url = None

        # Create a new category
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            slack_channel=data['slack_channel'],
            prompt=data.get('prompt', ''),
            time_interval=data.get('time_interval', 3),
            is_active=data.get('is_active', False),
            border_color=data.get('border_color', None),
            icon=image_url,
            created_at=datetime.now(),
        )

        db.session.add(new_category)
        db.session.commit()

        # Prepare the response with only necessary data
        return jsonify(create_response(success=True, data=new_category.as_dict())), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@measure_execution_time
@handle_db_session
def delete_category(category_id):
    """
    Delete a category by ID.
    Args:
        category_id (int): ID of the category to delete.
    Response:
        200: Category deleted successfully.
        404: Category not found.
        500: Internal server error or database error.
    """
    try:
        # Fetch the category from the database
        category = Category.query.get(category_id)
        if not category:
            return jsonify(create_response(error=f'Category with ID {category_id} not found')), 404

        # Delete the category
        db.session.delete(category)
        db.session.commit()

        return jsonify(create_response(success=True, data={'id': category_id})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@categories_bp.route('/categories', methods=['GET'])
@measure_execution_time
@handle_db_session
def get_categories():
    """
    Get all available categories.
    Response:
        200: Successfully retrieved categories.
        404: No categories found.
        500: Internal server error or database error.
    """
    try:
        categories = Category.query.all()

        if not categories:
            return jsonify(create_response(error='No categories found')), 404

        category_data = [category.as_dict() for category in categories]

        return jsonify(create_response(success=True, data={'categories': category_data})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@categories_bp.route('/get_all_bots', methods=['GET'])
@measure_execution_time
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
