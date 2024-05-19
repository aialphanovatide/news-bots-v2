from flask import Blueprint, jsonify, request
from config import Blacklist, Category, db

deactivate_bots_bp = Blueprint(
    'deactivate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Deactivate all categories
@deactivate_bots_bp.route('/deactivate_all_categories', methods=['POST'])
def deactivate_all_categories():
    try:
        # Fetch all categories from the database
        categories = Category.query.all()
        if not categories:
            return jsonify({'error': 'No categories found'}), 404

        for category in categories:
            # Set category as inactive
            category.is_active = False
        
        db.session.commit()  # Commit the changes to the database

        return jsonify({'message': 'All categories deactivated'}), 200

    except Exception as e:
        return jsonify({'error': f"Error deactivating all categories: {e}"}), 500


# Deactivate a single category
@deactivate_bots_bp.route('/deactivate_category', methods=['POST'])
def deactivate_category():
    try:
        # Get the category name from the request JSON
        category_name = request.json.get('category_name')
        if not category_name:
            return jsonify({'error': 'Category name is required'}), 400

        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        # Set category as inactive
        category.is_active = False
        db.session.commit()  # Commit the change to the database

        return jsonify({'message': f'{category_name} was deactivated successfully'}), 200

    except Exception as e:
        return jsonify({'error': f"Error deactivating category '{category_name}': {e}"}), 500
