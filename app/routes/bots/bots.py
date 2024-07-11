import re
from scheduler_config_1 import scheduler
from datetime import datetime
from app.utils.index import fetch_news_links
from flask import Blueprint, jsonify, request
from config import Blacklist, Bot, Keyword, Site, db, Category
from sqlalchemy.exc import SQLAlchemyError

bots_bp = Blueprint(
    'bots_bp', __name__,
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

@bots_bp.route('/bots', methods=['GET'])
def get_bots():
    """
    Get all available bots.
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
    Args:
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

        # Required inputs
        required_fields = ['name', 'category_id', 'url', 'keywords', 'blacklist', 'dalle_prompt']
        for field in required_fields:
            if field not in data:
                response['error'] = f'Missing field in request data: {field}'
                return jsonify(response), 400

        category_id = data['category_id']
        # Verify existing bot
        existing_bot = Bot.query.filter_by(name=data['name']).first()
        if existing_bot:
            response['error'] = f"A bot with the name '{data['name']}' already exists"
            return jsonify(response), 400

        # Verify if the category exists
        existing_category = Category.query.filter_by(id=str(category_id)).first()
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
        site_name = 'Google News'
        if site_name_match:
            site_name = site_name_match.group(1)

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

        # Check if there is a scheduled job for the bot
        bot_job = scheduler.get_job(job_id=str(bot_id))
        if bot_job:
            scheduler.remove_job(job_id=str(bot_id))

        # Delete bot and commit transaction
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
