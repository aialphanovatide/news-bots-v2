from flask import Blueprint, jsonify, request
from scheduler_config_1 import scheduler
from config import Category, db, Bot

deactivate_bots_bp = Blueprint(
    'deactivate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Deactivate all categories
@deactivate_bots_bp.route('/deactivate_all_categories', methods=['POST'])
def deactivate_all_categories():
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Fetch all categories from the database
        categories = Category.query.all()
        if not categories:
            response['error'] = 'No categories found'
            return jsonify(response), 404

        # Check if all categories are already deactivated
        if all(not category.is_active for category in categories):
            response['message'] = 'All categories are already deactivated'
            return jsonify(response), 200

        # Deactivate all categories
        for category in categories:
            # Set category as inactive
            category.is_active = False
        db.session.commit()
        
        # Remove all jobs from the scheduler
        scheduler.remove_all_jobs()

        response['message'] = 'All categories deactivated'
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f"Error deactivating all categories: {e}"
        return jsonify(response), 500




# Deactivate a single category
@deactivate_bots_bp.route('/deactivate_category', methods=['POST'])
def deactivate_category():
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Get the category name from the request JSON
        category_name = request.json.get('category_name')
        if not category_name:
            response['error'] = 'Category name is required'
            return jsonify(response), 400

        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            response['error'] = 'Category not found'
            return jsonify(response), 404
        
        # Remove bots from scheduler
        bot_names = [bot.name for bot in Bot.query.filter_by(category_id=category.id).all()]

        for name in bot_names:
            schedule_job = scheduler.get_job(id=str(name))
            if schedule_job:
                scheduler.remove_job(id=str(name))

        # Check if the category is already inactive
        if not category.is_active:
            response['message'] = f"{category_name} is already deactivated"
            return jsonify(response), 200

        # Set category as inactive
        category.is_active = False
        db.session.commit()  

        response['message'] = f"{category_name} was deactivated successfully"
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f"Error deactivating category '{category_name}': {e}"
        return jsonify(response), 500


