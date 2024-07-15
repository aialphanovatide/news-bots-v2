import re
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from app.utils.helpers import measure_execution_time
from scheduler_config_1 import scheduler
from config import Blacklist, Bot, Keyword, Site, db, Category
from app.utils.index import fetch_news_links

bots_bp = Blueprint(
    'bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Function to be scheduled
def scheduled_job(bot_site, bot_name, bot_blacklist, category_id, bot_id, category_slack_channel):
    """
    Function to fetch news links based on bot configuration.
    Args:
        bot_site (str): URL of the bot's site.
        bot_name (str): Name of the bot.
        bot_blacklist (list): List of blacklisted keywords.
        category_id (int): ID of the category.
        bot_id (int): ID of the bot.
        category_slack_channel (str): Slack channel for category notifications.
    """
    with scheduler.app.app_context():
        fetch_news_links(
            url=bot_site,
            bot_name=bot_name,
            blacklist=bot_blacklist,
            category_id=category_id,
            bot_id=bot_id,
            category_slack_channel=category_slack_channel
        )

@bots_bp.route('/bots', methods=['GET'])
def get_complete_bots():
    """
    Retrieve all available bots.
    Response:
        200: List of bots retrieved successfully.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        bots = Bot.query.all()
        bot_data = [bot.as_dict() for bot in bots]

        response['data'] = bot_data
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Error getting all Bots: {str(e)}'
        return jsonify(response), 500

@bots_bp.route('/create_bot', methods=['POST'])
async def create_bot():
    """
    Create and schedule a new news bot.
    Args (JSON):
        name (str): Name of the bot.
        category_id (int): ID of the category.
        url (str): URL to fetch news from.
        keywords (str): Comma-separated keywords for the bot.
        blacklist (str): Comma-separated blacklist for the bot.
        dalle_prompt (str): DALLE prompt for the bot.
    Response:
        200: Bot created (and scheduled if the category is active) successfully.
        400: Missing required field or bot name already exists.
        404: Category ID not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.json
        current_time = datetime.now()

        # Validate required fields
        required_fields = ['name', 'category_id', 'url', 'keywords', 'blacklist', 'dalle_prompt']
        for field in required_fields:
            if field not in data:
                response['error'] = f'Missing field in request data: {field}'
                return jsonify(response), 400

        # Check if bot with the same name already exists
        existing_bot = Bot.query.filter_by(name=data['name']).first()
        if existing_bot:
            response['error'] = f"A bot with the name '{data['name']}' already exists"
            return jsonify(response), 400

        # Check if the category exists
        existing_category = Category.query.get(data['category_id'])
        if not existing_category:
            response['error'] = 'Category ID not found'
            return jsonify(response), 404

        category_id = existing_category.id
        category_interval = existing_category.time_interval
        is_category_active = existing_category.is_active
        category_slack_channel = existing_category.slack_channel

        # Create new bot
        new_bot = Bot(
            name=data['name'],
            category_id=category_id,
            dalle_prompt=data['dalle_prompt'],
            created_at=current_time,
            updated_at=current_time
        )
        db.session.add(new_bot)
        db.session.commit()

        # Create new Site
        url = data['url']
        site_name_match = re.search(r"https://www\.([^.]+)\.com", url)
        site_name = 'Google News' if not site_name_match else site_name_match.group(1)

        new_site = Site(
            name=site_name,
            url=url,
            bot_id=new_bot.id,
            created_at=current_time,
            updated_at=current_time
        )
        db.session.add(new_site)
        db.session.commit()

        # Add keywords to the bot
        keywords = [keyword.strip() for keyword in data['keywords'].split(',')]
        for keyword in keywords:
            new_keyword = Keyword(
                name=keyword,
                bot_id=new_bot.id,
                created_at=current_time,
                updated_at=current_time
            )
            db.session.add(new_keyword)

        # Add words to the bot Blacklist
        blacklist = [keyword.strip() for keyword in data['blacklist'].split(',')]
        for word in blacklist:
            new_blacklist_entry = Blacklist(
                name=word,
                bot_id=new_bot.id,
                created_at=current_time,
                updated_at=current_time
            )
            db.session.add(new_blacklist_entry)

        db.session.commit()

        # Schedule the bot if the category is active
        if is_category_active:
            scheduler.add_job(
                id=str(new_bot.name),
                func=scheduled_job,
                name=new_bot.name,
                replace_existing=True,
                args=[url, new_bot.name, blacklist, existing_category.id, new_bot.id, category_slack_channel],
                trigger='interval',
                minutes=category_interval
            )
            response['message'] = 'Bot created and automated successfully'
        else:
            response['message'] = 'Bot created, but NOT automated - Activate the category'

        response['data'] = new_bot.as_dict()
        response['success'] = True
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        response['error'] = f"Error creating bot: {str(e)}"
        return jsonify(response), 500

@bots_bp.route('/delete_bot/<int:bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """
    Delete a single bot by ID.
    Args:
        bot_id (int): The ID of the bot to delete.
    Response:
        200: Bot deleted successfully.
        404: Bot not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot = Bot.query.get(bot_id)
        if not bot:
            response['error'] = 'Bot not found'
            return jsonify(response), 404

        # Remove scheduled job for the bot if exists
        bot_job = scheduler.get_job(job_id=str(bot_id))
        if bot_job:
            scheduler.remove_job(job_id=str(bot_id))

        # Delete bot from database
        db.session.delete(bot)
        db.session.commit()

        response['message'] = f'Bot with ID {bot_id} deleted successfully'
        response['success'] = True
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

@bots_bp.route('/get_all_bots', methods=['GET'])
def get_all_bots():
    """
    Retrieve all bots with associated categories.
    Response:
        200: List of bots retrieved successfully.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        categories = Category.query.order_by(Category.id).all()
        bots = [{'category': category.name, 'isActive': category.is_active, 
                 'alias': category.alias, 'icon': category.icon, 'updated_at': category.updated_at , 'color': category.border_color} for category in categories]
        response['data'] = bots
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Error retrieving bots: {str(e)}'
        return jsonify(response), 500

@bots_bp.route('/activate_bot_by_id/<category_name>', methods=['POST'])
def activate_bot_by_id(category_name):
    """
    Activate all bots associated with a given category.
    Args:
        category_name (str): The name of the category to activate bots for.
    Response:
        200: Category activated successfully.
        404: Category not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            response['error'] = 'Category not found'
            return jsonify(response), 404

        # Check if the category is already active
        if category.is_active:
            response['message'] = f"{category_name} category is already active"
            return jsonify(response), 200

        # Fetch all bots associated with the category
        bots = Bot.query.filter_by(category_id=category.id).all()

        interval_base = 20  # Base interval in minutes

        for index, bot in enumerate(bots):
            # Fetch the associated site for the bot
            site = Site.query.filter_by(bot_id=bot.id).first()
            if not site or not site.url:
                continue  # Skip if no site or site URL is found

            # Prepare data for scheduling
            bot_site = site.url
            bot_blacklist = [bl.name for bl in Blacklist.query.filter_by(bot_id=bot.id).all()]
            bot_id = bot.id
            bot_name = bot.name

            # Calculate interval based on the index of the bot
            minutes = interval_base + 10 * index

            scheduler.add_job(
                id=str(bot_name),
                func=scheduled_job,
                name=bot_name,
                replace_existing=True,
                args=[bot_site, bot_name, bot_blacklist, category.id, bot_id, category.slack_channel],
                trigger='interval',
                minutes=minutes
            )
            
        # Set category as active
        category.is_active = True
        db.session.commit()

        response['message'] = f'{category_name} category was activated successfully'
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f"Error activating bots for category '{category_name}': {e}"
        return jsonify(response), 500


@bots_bp.route('/deactivate_bot_by_id/<category_name>', methods=['POST'])
def deactivate_bot_by_id(category_name):
    """
    Deactivate all bots associated with a given category.
    Args:
        category_name (str): The name of the category to deactivate bots for.
    Response:
        200: Category deactivated successfully.
        404: Category not found.
        500: Internal server error.
    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            response['error'] = 'Category not found'
            return jsonify(response), 404
        
        # Remove scheduled jobs for all bots in the category
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

@bots_bp.route('/get_all_coin_bots', methods=['GET'])
def get_all_coin_bots():
    """
    Get all coin bots.
    Response:
        200: List of coin bots retrieved successfully.
        500: Internal server error.
    """
    try:
        response = {'data': None, 'error': None, 'success': False}
        coin_bots = db.session.query(Bot.id, Bot.name).all()
        coin_bots_data = [{'id': id, 'name': name } for id, name in coin_bots]
        return jsonify({'success': True, 'coin_bots': coin_bots_data}), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
