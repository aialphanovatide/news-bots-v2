from datetime import datetime
import os
from flask import Blueprint, json, jsonify
from config import Category
from flask import request
from config import db
from dotenv import load_dotenv
import boto3

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')

categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Create a new category

s3 = boto3.client(
            's3',
            region_name='us-east-2',
            aws_access_key_id=AWS_ACCESS,
            aws_secret_access_key=AWS_SECRET_KEY
        )

@categories_bp.route('/add_new_category', methods=['POST'])
def create_category():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = json.loads(request.form.get('data'))

        # Input validation for required fields
        required_fields = ['name', 'alias', 'prompt', 'time_interval', 'slack_channel']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify(response), 400

        # Check if the category already exists
        existing_category = Category.query.filter_by(name=str(data['name']).casefold()).first()
        if existing_category:
            response['error'] = f'Category {data["name"]} already exists'
            return jsonify(response), 400

        # Upload the image to S3
        if 'image' in request.files:
            image_file = request.files['image']
            image_filename = f'{data['alias']}.png'
            print("image_filename", image_filename)
            s3.upload_fileobj(image_file, 'aialphaicons', image_filename)
            image_url = f'https://aialphaicons.s3.amazonaws.com/{image_filename}'
            print("image_url", image_url)
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
        response['data'] = new_category.as_dict()
        response['success'] = True
        return jsonify(response), 201

    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500



# Delete a category by ID
@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):

    response = {'data': None, 'error': None, 'success': False}
    try:
        # Fetch the category from the database
        category = Category.query.get(category_id)
        if not category:
            response['error'] = f'Category with ID {category_id} not found'
            return jsonify(response), 404

        # Delete the category
        db.session.delete(category)
        db.session.commit()

        response['data'] = {'id': category_id}
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500


    
# Get all available categories
@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    response = {'data': None, 'error': None, 'success': False}
    try:
        categories = Category.query.all()

        if not categories:
            response['error'] = 'No categories found'
            return jsonify(response), 404

        category_data = [category.as_dict() for category in categories]

        response['data'] = {'categories': category_data}
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500

# Get all bots
@categories_bp.route('/get_all_bots', methods=['GET'])
def get_bots():
    response = {'data': None, 'error': None, 'success': False}
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
        response['data'] = {'bots': bots}
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error {str(e)}'
        return jsonify(response), 500