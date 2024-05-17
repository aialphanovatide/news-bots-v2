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

@categories_bp.route('/add_new_category', methods=['POST'])
def create_category():
    try:
        data = request.get_json()
        
        if 'name' not in data or 'alias' not in data or 'prompt' not in data or 'time_interval' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        name = data['name']
        existing_category = Category.query.filter_by(name=str(name).casefold()).first()
        if existing_category:
            return jsonify({'error': f'Category {name} already exist'}), 400
        
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            prompt=data.get('prompt', ''),
            time_interval=data.get('time_interval', None),
            is_active=data.get('is_active', False),
            border_color=data.get('border_color', None),
            icon=data.get('icon', None)
        )
        
        db.session.add(new_category)
        db.session.commit()
        
        return jsonify({
            'id': new_category.id,
            'name': new_category.name,
            'alias': new_category.alias,
            'prompt': new_category.prompt,
            'time_interval': new_category.time_interval,
            'is_active': new_category.is_active,
            'border_color': new_category.border_color,
            'icon': new_category.icon
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

    
# Get all available categories
@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        category_data = []
        for category in categories:
            category_data.append({
                'id': category.id,
                'name': category.name,
                'alias': category.alias,
                'prompt': category.prompt,
                'time_interval': category.time_interval,
                'is_active': category.is_active,
                'border_color': category.border_color,
                'icon': category.icon,
            })
        return jsonify({'message': category_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
