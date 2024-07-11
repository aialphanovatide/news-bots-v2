from flask import Blueprint, jsonify, request
from scheduler_config_1 import scheduler
from config import Category, db, Bot
from sqlalchemy.exc import SQLAlchemyError


deactivate_bots_bp = Blueprint(
    'deactivate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@deactivate_bots_bp.route('/deactivate_all_categories', methods=['POST'])
def deactivate_all_categories():
    """
    Deactivate all categories and remove all jobs from the scheduler.
    Response:
        200: All categories deactivated successfully or already deactivated.
        404: No categories found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        categories = Category.query.all()
        if not categories:
            response['error'] = 'No categories found'
            return jsonify(response), 404

        if all(not category.is_active for category in categories):
            response['message'] = 'All categories are already deactivated'
            response['success'] = True
            return jsonify(response), 200

        for category in categories:
            category.is_active = False
        db.session.commit()

        scheduler.remove_all_jobs()

        response['message'] = 'All categories deactivated'
        response['success'] = True
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        response['error'] = f"Error deactivating all categories: {e}"
        return jsonify(response), 500

@deactivate_bots_bp.route('/deactivate_category', methods=['POST'])
def deactivate_category():
    """
    Deactivate a single category and remove its associated bots from the scheduler.
    Args:
        category_name (str): Name of the category to deactivate.
    Response:
        200: Category deactivated successfully or already deactivated.
        400: Category name is required.
        404: Category not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        category_name = request.json.get('category_name')
        if not category_name:
            response['error'] = 'Category name is required'
            return jsonify(response), 400

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            response['error'] = 'Category not found'
            return jsonify(response), 404

        bot_names = [bot.name for bot in Bot.query.filter_by(category_id=category.id).all()]

        for name in bot_names:
            scheduled_job = scheduler.get_job(id=str(name))
            if scheduled_job:
                scheduler.remove_job(id=str(name))

        if not category.is_active:
            response['message'] = f"{category_name} is already deactivated"
            response['success'] = True
            return jsonify(response), 200

        category.is_active = False
        db.session.commit()

        response['message'] = f"{category_name} was deactivated successfully"
        response['success'] = True
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        response['error'] = f"Error deactivating category '{category_name}': {e}"
        return jsonify(response), 500
