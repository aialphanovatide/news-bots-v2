from flask import Blueprint, jsonify, request
from config import Blacklist, Category, Bot, Site, db
from datetime import datetime
from app.utils.index import fetch_news_links
from scheduler_config import scheduler
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

activate_bots_bp = Blueprint(
    'activate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Function to be scheduled
def scheduled_job(bot_site, bot_name, bot_blacklist, category_id, bot_id, category_slack_channel):
    with scheduler.app.app_context():
        fetch_news_links(
            url=bot_site,
            bot_name=bot_name,
            blacklist=bot_blacklist,
            category_id=category_id,
            bot_id=bot_id,
            category_slack_channel=category_slack_channel
        )
        try:
            category = Category.query.filter_by(id=category_id).first()
            if category:
                category.updated_at = datetime.now()
                db.session.commit()
                print(f'{category_id} updated successfully')
            else:
                print(f'Category {category_id} not found in the database')
        except Exception as e:
            print(f'Error updating {category_id}: {str(e)}')

@activate_bots_bp.route('/activate_all_categories', methods=['POST'])
@handle_db_session
def activate_all_bots():
    """
    Activate all bots for all categories.
    
    Response:
        200: All categories activated successfully.
        404: No categories found.
        500: Internal server error.
    """
    try:
        categories = Category.query.all()
        if not categories:
            return create_response(error='No categories found'), 404

        global_minutes = 10
        interval_base = 23  # Changed to 23 min to keep intervals between bots activation

        for category in categories:
            category_id = category.id
            category_slack_channel = category.slack_channel

            bots = Bot.query.filter_by(category_id=category_id).all()
            if not bots:
                continue

            for bot in bots:
                site = Site.query.filter_by(bot_id=bot.id).first()
                if not site or not site.url:
                    continue

                bot_site = site.url
                bot_blacklist = [bl.name for bl in Blacklist.query.filter_by(bot_id=bot.id).all()]
                bot_id = bot.id
                bot_name = bot.name

                # Ensure a unique interval for each bot
                minutes = global_minutes
                scheduler.add_job(
                    id=str(bot_name),
                    func=scheduled_job,
                    name=bot_name,
                    replace_existing=True,
                    args=[bot_site, bot_name, bot_blacklist, category.id, bot_id, category_slack_channel],
                    trigger='interval',
                    minutes=minutes
                )

                # Increment global minutes for next bot
                global_minutes += interval_base

                category.is_active = True
                db.session.commit()

        return create_response(success=True, message='All categories activated'), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}'), 500

    except Exception as e:
        return create_response(error=f"Error activating all bots: {e}"), 500


@activate_bots_bp.route('/activate_category', methods=['POST'])
@handle_db_session
def activate_bots_by_category():
    """
    Activate bots for a single category.
    Args:
        category_name (str): The name of the category to activate.
    Response:
        200: Category activated successfully or already active.
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

        category_interval = category.time_interval
        category_slack_channel = category.slack_channel
        if category.is_active:
            return create_response(success=True, message=f"{category_name} category is already active"), 200

        bots = Bot.query.filter_by(category_id=category.id).all()
        interval_base = 20  # Base interval in minutes

        for index, bot in enumerate(bots):
            site = Site.query.filter_by(bot_id=bot.id).first()
            if not site or not site.url:
                continue

            bot_site = site.url
            bot_blacklist = [bl.name for bl in Blacklist.query.filter_by(bot_id=bot.id).all()]
            bot_id = bot.id
            bot_name = bot.name

            minutes = category_interval + 10 * index

            scheduler.add_job(
                id=str(bot_name),
                func=scheduled_job,
                name=bot_name,
                replace_existing=True,
                args=[bot_site, bot_name, bot_blacklist, category.id, bot_id, category_slack_channel],
                trigger='interval',
                minutes=1
            )
            
        category.is_active = True
        db.session.commit()

        return create_response(success=True, message=f'{category_name} category was activated successfully'), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}'), 500

    except Exception as e:
        return create_response(error=f"Error activating bots for category '{category_name}': {e}"), 500




@activate_bots_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """
    List all scheduled jobs.
    Response:
        200: Successfully retrieved the list of jobs.
        500: Internal server error.
    """
    try:
        jobs = scheduler.get_jobs()
        job_list = [{'id': job.id, 'name': job.name, 'next_run_time': job.next_run_time} for job in jobs]
        return create_response(success=True, data=job_list), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f'Database error: {str(e)}'), 500
    
    except Exception as e:
        return create_response(error=f"Error listing jobs: {e}"), 500
