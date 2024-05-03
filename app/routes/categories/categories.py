from flask import Blueprint, jsonify
from config import Category

categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    category_data = []
    for category in categories:
        category_data.append({
            'id': category.id,
            'name': category.name,
            'alias': category.alias,
            'time_interval': category.time_interval,
            'is_active': category.is_active,
            'border_color': category.border_color,
            'icon': category.icon,
        })
    return jsonify(category_data)