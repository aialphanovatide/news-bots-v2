from datetime import datetime
from flask import Blueprint, jsonify
from config import Category
from flask import request
from config import db
import requests

categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Create a new category
@categories_bp.route('/add_new_category', methods=['POST'])
def create_category():

    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.get_json()

        # Input validation for required fields
        required_fields = ['name', 'alias', 'prompt', 'time_interval']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response['error'] = f'Missing required fields: {", ".join(missing_fields)}'
            return jsonify(response), 400

        name = data['name']

        # Check if the category already exists
        existing_category = Category.query.filter_by(name=str(name).casefold()).first()
        if existing_category:
            response['error'] = f'Category {name} already exists'
            return jsonify(response), 400

        # Create a new category
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            prompt=data.get('prompt', ''),
            time_interval=data.get('time_interval', 3),
            is_active=data.get('is_active', False),
            border_color=data.get('border_color', None),
            icon=data.get('icon', None),
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

