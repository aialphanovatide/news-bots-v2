import re
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from app.utils.helpers import measure_execution_time
from scheduler_config import reschedule, scheduler
from config import Blacklist, Bot, Keyword, Session, Site, db, Category
from app.utils.index import fetch_news_links
from app.routes.routes_utils import create_response, handle_db_session

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

def get_bot_with_related_info(bot):
    bot_dict = bot.as_dict()
    bot_dict['keywords'] = [keyword.name for keyword in bot.keywords]
    bot_dict['blacklist'] = [item.name for item in bot.blacklist]
    return bot_dict

@bots_bp.route('/bot', methods=['GET'])
def get_bot():
    """
    Get a specific bot by name or id, including related keywords and blacklist items.
    Parameters:
    - name: string (optional)
    - id: integer (optional)
    Response:
    200: Bot information retrieved successfully.
    404: Bot not found.
    400: Invalid parameters.
    500: Internal server error.
    """
    bot_name = request.args.get('bot_name')
    bot_id = request.args.get('bot_id')

    if not bot_name and not bot_id:
        return jsonify(create_response(error="Please provide either 'name' or 'id' parameter")), 400

    try:
        if bot_id:
            bot = Bot.query.options(db.joinedload(Bot.keywords), db.joinedload(Bot.blacklist)).get(bot_id)
        else:
            bot = Bot.query.options(db.joinedload(Bot.keywords), db.joinedload(Bot.blacklist)).filter_by(name=bot_name).first()

        if not bot:
            return jsonify(create_response(error="Bot not found")), 404

        response = create_response(success=True, data=get_bot_with_related_info(bot))
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f"Database error: {str(e)}")), 500
    except Exception as e:
        return jsonify(create_response(error=f"Unexpected error: {str(e)}")), 500

@bots_bp.route('/bots', methods=['GET'])
def get_all_bots():
    """
    Get all bots, including related keywords and blacklist items for each bot.
    Response:
    200: List of all bots retrieved successfully.
    500: Internal server error.
    """
    try:
        bots = Bot.query.options(db.joinedload(Bot.keywords), db.joinedload(Bot.blacklist)).all()
        bots_data = [get_bot_with_related_info(bot) for bot in bots]
        response = create_response(success=True, data=bots_data)
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f"Database error: {str(e)}")), 500
    except Exception as e:
        return jsonify(create_response(error=f"Unexpected error: {str(e)}")), 500


@bots_bp.route('/bots', methods=['POST'])
def create_bot():
    """
    Create a new bot and optionally schedule it.

    This endpoint handles the creation of a new bot with associated site, keywords, and blacklist.
    If the category is active and a URL is provided, it also schedules the bot.

    Request JSON:
        name (str): The name of the bot (required)
        alias (str): An alias for the bot (required)
        category_id (int): The ID of the category the bot belongs to (required)
        dalle_prompt (str): The DALL-E prompt for the bot (optional)
        background_color (str): The background color for the bot (optional)
        run_frequency (int): The frequency to run the bot in minutes (optional)
        url (str): The URL for the bot's site (optional)
        whitelist (str): Comma-separated list of keywords (optional)
        blacklist (str): Comma-separated list of blacklisted words (optional)

    Returns:
        JSON: A response containing:
            - success (bool): Indicates if the operation was successful
            - bot (dict): The created bot's data
            - error (str): Error message if any
            - message (str): Additional information about the operation
        HTTP Status Code:
            - 201: Created successfully
            - 400: Bad request (missing required fields or bot name already exists)
            - 404: Category not found
            - 500: Internal server error
    """
    response = {
        "success": False,
        "bot": None,
        "error": None,
        "message": ""
    }
    status_code = 500
    with Session() as session:
        try:
            data = request.json
            current_time = datetime.now()

            # Validate required fields
            required_fields = ['name', 'alias', 'category_id', 'url']
            for field in required_fields:
                if field not in data:
                    response["error"] = f'Missing field in request data: {field}'
                    return jsonify(response), 400

            # Check if bot with the same name already exists
            existing_bot = session.query(Bot).filter_by(name=data['name']).first()
            if existing_bot:
                response["error"] = f"A bot with the name '{data['name']}' already exists"
                return jsonify(response), 400

            # Check if the category exists
            existing_category = session.query(Category).get(data['category_id'])
            if not existing_category:
                response["error"] = 'Category ID not found'
                return jsonify(response), 404
            
            icon_normalized = data["alias"].strip().replace(" ", "_").lower()
            # Create new bot
            new_bot = Bot(
                name=data['name'],
                alias=data['alias'],
                category_id=data['category_id'],
                dalle_prompt=data.get('dalle_prompt', ''),
                icon=f'https://aialphaicons.s3.us-east-2.amazonaws.com/{icon_normalized}.svg',
                background_color=data.get('background_color', ''),
                run_frequency=data.get('run_frequency', ''),
                is_active=False,
                created_at=current_time,
                updated_at=current_time
            )
            session.add(new_bot)
            session.flush() 

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
            session.add(new_site)

            # Add keywords (whitelist) to the bot
            if 'whitelist' in data:
                keywords = [keyword.strip() for keyword in data['whitelist'].split(',')]
                for keyword in keywords:
                    new_keyword = Keyword(
                        name=keyword,
                        bot_id=new_bot.id,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    session.add(new_keyword)

            # Add words to the bot Blacklist
            blacklist = []
            if 'blacklist' in data:
                blacklist = [keyword.strip() for keyword in data['blacklist'].split(',')]
                for word in blacklist:
                    new_blacklist_entry = Blacklist(
                        name=word,
                        bot_id=new_bot.id,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    session.add(new_blacklist_entry)

            session.commit()

            # Schedule the bot if the category is active
            if existing_category.is_active:
                try:
                    scheduler.add_job(
                        id=str(new_bot.name),
                        func=scheduled_job,
                        name=new_bot.name,
                        replace_existing=True,
                        args=[url, new_bot.name, blacklist, existing_category.id, new_bot.id, existing_category.slack_channel],
                        trigger='interval',
                        minutes=int(new_bot.run_frequency)
                    )
                    response["message"] = "Bot created and scheduled successfully"
                except Exception as e:
                    response["message"] = f"Bot created but scheduling failed: {str(e)}"
            else:
                response["message"] = "Bot created but not scheduled (category inactive)"

            response["success"] = True
            response["bot"] = new_bot.as_dict()
            status_code = 201

        except SQLAlchemyError as e:
            session.rollback()
            response["error"] = f"Database error: {str(e)}"
        except Exception as e:
            response["error"] = f"An unexpected error occurred: {str(e)}"

    return jsonify(response), status_code


@bots_bp.route('/bots/<int:bot_id>/toggle-publication', methods=['POST'])
def toggle_bot_publication(bot_id):
    """
    Toggle the publication status of a bot.

    This endpoint activates or deactivates a bot based on its current status.
    It performs necessary validations and schedules or unschedules the bot as needed.

    Args:
        bot_id (int): The ID of the bot to toggle

    Returns:
        JSON: A response containing:
            - success (bool): Indicates if the operation was successful
            - message (str): A message describing the result of the operation
            - error (str or None): Error message, if any
        HTTP Status Code:
            - 200: Operation successful
            - 404: Bot not found
            - 400: Validation failed
            - 500: Internal server error
    """
    response = {
        "success": False,
        "message": "",
        "error": None
    }
    status_code = 500

    with Session() as session:
        try:
            bot = session.query(Bot).get(bot_id)
            if not bot:
                response["error"] = f"No bot found with ID: {bot_id}"
                return jsonify(response), 404

            # Validation for activation
            if not bot.is_active:
                # Check if the bot has an associated site
                site = session.query(Site).filter_by(bot_id=bot.id).first()
                if not site or not site.url:
                    response["error"] = "Bot does not have an associated site URL"
                    return jsonify(response), 400

                # Additional validations can be added here

            # Toggle bot status
            bot.is_active = not bot.is_active
            
            if bot.is_active:
                # Activation logic
                site = session.query(Site).filter_by(bot_id=bot.id).first()
                bot_blacklist = [bl.name for bl in session.query(Blacklist).filter_by(bot_id=bot.id).all()]
                category = session.query(Category).get(bot.category_id)

                try:
                    scheduler.add_job(
                        id=str(bot.name),
                        func=scheduled_job,
                        name=bot.name,
                        replace_existing=True,
                        args=[site.url, bot.name, bot_blacklist, category.id, bot.id, category.slack_channel],
                        trigger='interval',
                        minutes=int(bot.run_frequency)
                    )
                    response["message"] = f"Bot {bot.name} activated and scheduled successfully"
                except Exception as e:
                    response["error"] = f"Failed to schedule bot: {str(e)}"
                    return jsonify(response), 500
            else:
                # Deactivation logic
                try:
                    scheduler.remove_job(id=str(bot.name))
                    response["message"] = f"Bot {bot.name} deactivated and unscheduled successfully"
                except Exception:
                    response["message"] = f"Bot {bot.name} deactivated (was not scheduled)"

            bot.updated_at = datetime.now()
            session.commit()

            response["success"] = True
            status_code = 200

        except SQLAlchemyError as e:
            session.rollback()
            response["error"] = f"Database error occurred: {str(e)}"
            status_code = 500
        except Exception as e:
            session.rollback()
            response["error"] = f"An unexpected error occurred: {str(e)}"
            status_code = 500

    return jsonify(response), status_code


@bots_bp.route('/bots/<int:bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """
    Update an existing bot in the news bot server and reschedule if necessary.

    This endpoint updates a bot entry with the provided details, saves the changes to the database,
    and reschedules the bot if it's active and its run frequency has changed.

    Args:
        bot_id (int): The ID of the bot to be updated

    Request JSON:
        name (str, optional): The name of the bot
        alias (str, optional): An alternative identifier for the bot
        category_id (int, optional): The ID of the category the bot belongs to
        dalle_prompt (str, optional): The DALL-E prompt for the bot
        background_color (str, optional): HEX code string for visual representation
        run_frequency (int, optional): The frequency to run the bot in minutes
        url (str, optional): The URL for the bot's site
        whitelist (str, optional): Comma-separated list of keywords
        blacklist (str, optional): Comma-separated list of blacklisted words

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - bot (dict or None): The updated bot data or None
            - error (str or None): Error message, if any
            - message (str): Additional information about the operation
        HTTP Status Code:
            - 200: Updated successfully
            - 400: Bad request (invalid data)
            - 404: Bot not found
            - 500: Internal server error
    """
    response = {
        "success": False,
        "bot": None,
        "error": None,
        "message": ""
    }
    status_code = 500

    with Session() as session:
        try:
            bot = session.query(Bot).get(bot_id)
            if not bot:
                response["error"] = f'Bot with ID {bot_id} not found'
                return jsonify(response), 404

            data = request.json
            if not data:
                response["error"] = 'No update data provided'
                return jsonify(response), 400


            # Update fields if provided
            updatable_fields = ['name', 'alias', 'category_id', 'dalle_prompt', 'background_color', 'run_frequency']
            for field in updatable_fields:
                if field in data:
                    setattr(bot, field, data[field])

            # Update Site if URL is provided
            if 'url' in data:
                site = session.query(Site).filter_by(bot_id=bot.id).first()
                if site:
                    site.url = data['url']
                else:
                    new_site = Site(
                        name=f"{bot.name} Site",
                        url=data['url'],
                        bot_id=bot.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_site)

            # Update keywords (whitelist)
            if 'whitelist' in data:
                session.query(Keyword).filter_by(bot_id=bot.id).delete()
                keywords = [keyword.strip() for keyword in data['whitelist'].split(',')]
                for keyword in keywords:
                    new_keyword = Keyword(
                        name=keyword,
                        bot_id=bot.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_keyword)

            # Update blacklist
            if 'blacklist' in data:
                session.query(Blacklist).filter_by(bot_id=bot.id).delete()
                blacklist = [word.strip() for word in data['blacklist'].split(',')]
                for word in blacklist:
                    new_blacklist_entry = Blacklist(
                        name=word,
                        bot_id=bot.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_blacklist_entry)

            bot.updated_at = datetime.now()
            session.commit()

            # Reschedule the bot if it's active and run_frequency has changed
            if bot.is_active:
                try:
                    reschedule(str(bot.name), minutes=int(bot.run_frequency))
                    response["message"] = "Bot updated and rescheduled successfully"
                except Exception as e:
                    response["message"] = f"Bot updated but rescheduling failed: {str(e)}"
            else:
                response["message"] = "Bot updated successfully"

            response["success"] = True
            response["bot"] = bot.as_dict()
            status_code = 200

        except SQLAlchemyError as e:
            session.rollback()
            response["error"] = f"Database error: {str(e)}"
        except Exception as e:
            response["error"] = f"An unexpected error occurred: {str(e)}"

    return jsonify(response), status_code


@bots_bp.route('/bots/<int:bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """
    Delete a bot and all its associated data from the news bot server.

    This endpoint deletes a bot entry identified by the provided ID. Due to the cascade
    configuration, it will also delete all associated sites, keywords, blacklist entries,
    articles, and unwanted articles.

    Args:
        bot_id (int): The ID of the bot to be deleted

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - message (str): A message describing the result of the operation
            - error (str or None): Error message, if any
        HTTP Status Code:
            - 200: Deleted successfully
            - 404: Bot not found
            - 500: Internal Server Error
    """
    response = {
        "success": False,
        "message": "",
        "error": None
    }
    status_code = 500

    with Session() as session:
        try:
            bot = session.query(Bot).get(bot_id)
            if not bot:
                response["error"] = f"No bot found with ID: {bot_id}"
                status_code = 404
                return jsonify(response), status_code

            bot_job = scheduler.get_job(id=str(bot.name))  
            if bot_job:
                scheduler.remove_job(id=str(bot.name)) 
            else:
                print(f"No job found for bot {bot.name}")

            session.delete(bot)
            session.commit()

            response["success"] = True
            response["message"] = f"Bot with ID {bot_id} and all its associated data have been successfully deleted"
            status_code = 200

        except SQLAlchemyError as e:
            session.rollback()
            response["error"] = f"Database error occurred: {str(e)}"
            status_code = 500
        except Exception as e:
            session.rollback()
            response["error"] = f"An unexpected error occurred: {str(e)}"
            status_code = 500

    return jsonify(response), status_code