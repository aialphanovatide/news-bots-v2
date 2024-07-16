# routes.py

from flask import Blueprint, jsonify, request
from scheduler_config import scheduler
from config import Category, db, Bot
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

deactivate_bots_bp = Blueprint(
    'deactivate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@deactivate_bots_bp.route('/deactivate_all_categories', methods=['POST'])
@handle_db_session
def deactivate_all_categories():
    """
    Deactivate all categories and remove all jobs from the scheduler.
    Response:
        200: All categories deactivated successfully or already deactivated.
        404: No categories found.
        500: Internal server error.
    """
    try:
        categories = Category.query.all()
        if not categories:
            return create_response(error='No categories found'), 404

        if all(not category.is_active for category in categories):
            return create_response(success=True, message='All categories are already deactivated'), 200

        for category in categories:
            category.is_active = False
        db.session.commit()

        scheduler.remove_all_jobs()

        return create_response(success=True, message='All categories deactivated'), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}'), 500
    
    except Exception as e:
        return create_response(error=f"Error deactivating all categories: {e}"), 500

@deactivate_bots_bp.route('/deactivate_category', methods=['POST'])
@handle_db_session
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
    try:
        category_name = request.json.get('category_name')
        if not category_name:
            return create_response(error='Category name is required'), 400

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return create_response(error='Category not found'), 404

        bot_names = [bot.name for bot in Bot.query.filter_by(category_id=category.id).all()]

        for name in bot_names:
            scheduled_job = scheduler.get_job(id=str(name))
            if scheduled_job:
                scheduler.remove_job(id=str(name))

        if not category.is_active:
            return create_response(success=True, message=f"{category_name} is already deactivated"), 200

        category.is_active = False
        db.session.commit()

        return create_response(success=True, message=f"{category_name} was deactivated successfully"), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}'), 500
    
    except Exception as e:
        return create_response(error=f"Error deactivating category '{category_name}': {e}"), 500
