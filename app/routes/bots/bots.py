import re
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from app.routes.bots.utils import validate_url
from flask import current_app
from scheduler_config import scheduler
from app.routes.routes_utils import create_response
from config import Blacklist, Bot, Keyword, Metrics, Session, Site, db, Category
from app.routes.bots.utils import schedule_bot, validate_bot_for_activation
from redis_client.redis_client import cache_with_redis, update_cache_with_redis
import csv
import json
from flask import Response
from sqlalchemy import func

bots_bp = Blueprint(
    'bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@bots_bp.route('/bot', methods=['GET'])
@cache_with_redis()
def get_bot():
    """
    Get a specific bot by name or id, including related keywords, blacklist items, and site data.
    
    Parameters:
    - bot_name: string (optional)
    - bot_id: integer (optional)
    
    Response:
    200: Bot information retrieved successfully.
    404: Bot not found.
    400: Invalid parameters.
    500: Internal server error.
    """
    bot_name = request.args.get('bot_name')
    bot_id = request.args.get('bot_id')

    if not bot_name and not bot_id:
        return jsonify(create_response(error="Please provide either 'bot_name' or 'bot_id' parameter")), 400

    try:
        query = Bot.query.options(
            joinedload(Bot.keywords),
            joinedload(Bot.blacklist),
            joinedload(Bot.sites)
        )
        
        if bot_id:
            bot = query.get(bot_id)
        else:
            bot = query.filter_by(name=bot_name).first()

        if not bot:
            return jsonify(create_response(error="Bot not found")), 404

        bot_dict = bot.as_dict()
        bot_dict['keywords'] = sorted([keyword.name for keyword in bot.keywords])
        bot_dict['blacklist'] = sorted([item.name for item in bot.blacklist])
        
        # Add site data using the Site model's as_dict() method
        site = Site.query.filter_by(bot_id=bot.id).first()
        bot_dict['site'] = site.as_dict() if site else None

        response = create_response(success=True, data=bot_dict)
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f"Database error: {str(e)}")), 500
    except Exception as e:
        return jsonify(create_response(error=f"Unexpected error: {str(e)}")), 500


@bots_bp.route('/bots', methods=['GET'])
@cache_with_redis()
def get_all_bots():
    """
    Get all bots data.
    
    Response:
    200: List of all bots retrieved successfully, sorted alphabetically by bot name.
    500: Internal server error.
    """
    try:
        bots = Bot.query.all()
        
        bots_data = [bot.as_dict() for bot in bots]
        
        # Sort bots alphabetically by name
        bots_data.sort(key=lambda x: x['name'])
        
        response = create_response(success=True, data=bots_data)
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f"Database error: {str(e)}")), 500
    except Exception as e:
        return jsonify(create_response(error=f"Unexpected error: {str(e)}")), 500


@bots_bp.route('/bot', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_all_bots'])
def create_bot():
    """
    Create a new bot.

    This endpoint handles the creation of a new bot with associated site, keywords, and blacklist.

    Request JSON:
        name (str): The name of the bot (required)
        alias (str): An alias for the bot (required)
        category_id (int): The ID of the category the bot belongs to (required)
        dalle_prompt (str): The DALL-E prompt for the bot (optional)
        background_color (str): The background color for the bot (optional)
        run_frequency (int): The frequency to run the bot in minutes (required for scheduling, minimum 20 minutes)
        url (str): The URL for the bot's site (required for scheduling)
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
            - 400: Bad request (missing required fields, bot name already exists, or invalid run frequency)
            - 404: Category not found
            - 500: Internal server error
    """
    with Session() as session:
        try:
            data = request.json
            current_time = datetime.now()

            # Validate required fields
            required_fields = ['name', 'alias', 'category_id', 'run_frequency']
            for field in required_fields:
                if field not in data:
                    return jsonify(create_response(error=f'Missing field in request data: {field}')), 400

            # Validate run_frequency
            run_frequency = data.get('run_frequency')
            if not isinstance(run_frequency, int) or run_frequency < 20:
                return jsonify(create_response(error='Run frequency must be an integer of at least 20 minutes')), 400

            # Check if bot with the same name already exists
            existing_bot = session.query(Bot).filter_by(name=data['name']).first()
            if existing_bot:
                return jsonify(create_response(error=f"A bot with the name '{data['name']}' already exists")), 400

            # Check if the category exists
            existing_category = session.query(Category).get(data['category_id'])
            if not existing_category:
                return jsonify(create_response(error='Category ID not found')), 404
            
            # Normalize icon name
            icon_normalized = data["alias"].strip().replace(" ", "_").lower()
            
            # Create new bot
            new_bot = Bot(
                name=data['name'],
                alias=data['alias'],
                category_id=data['category_id'],
                dalle_prompt=data.get('dalle_prompt', ''),
                prompt=data.get('prompt', ''),
                icon=f'https://aialphaicons.s3.us-east-2.amazonaws.com/{icon_normalized}.svg',
                background_color=data.get('background_color', ''),
                run_frequency=run_frequency,
                is_active=False,
                created_at=current_time,
                updated_at=current_time
            )
            session.add(new_bot)
            session.flush() 

            # Create new Site if URL is provided
            url = data.get('url')
            if url:
                if not validate_url(url):
                    return jsonify(create_response(error='Invalid URL provided')), 400
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

            # Validate and add keywords (whitelist) to the bot
            if 'whitelist' in data:
                if not isinstance(data['whitelist'], str):
                    return jsonify(create_response(error='Whitelist must be a comma-separated string')), 400
                keywords = [keyword.strip().lower() for keyword in data['whitelist'].split(',') if keyword.strip()]
                for keyword in keywords:
                    new_keyword = Keyword(
                        name=keyword,
                        bot_id=new_bot.id,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    session.add(new_keyword)

            # Validate and add words to the bot Blacklist
            if 'blacklist' in data:
                if not isinstance(data['blacklist'], str):
                    return jsonify(create_response(error='Blacklist must be a comma-separated string')), 400
                blacklist = [word.strip().lower() for word in data['blacklist'].split(',') if word.strip()]
                for word in blacklist:
                    new_blacklist_entry = Blacklist(
                        name=word,
                        bot_id=new_bot.id,
                        created_at=current_time,
                        updated_at=current_time
                    )
                    session.add(new_blacklist_entry)

            session.commit()

            schedule_message = "Bot created successfully."
            return jsonify(create_response(
                success=True,
                bot=new_bot.as_dict(),
                message=schedule_message
            )), 201

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f"Database error: {str(e)}")), 500
        except Exception as e:
            return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), 500


@bots_bp.route('/bot/<int:bot_id>', methods=['PUT'])
@update_cache_with_redis(related_get_endpoints=['get_all_bots','get_bot'])
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
        prompt (str, optional): The general prompt for the bot
        background_color (str, optional): HEX code string for visual representation
        run_frequency (int, optional): The frequency to run the bot in minutes
        url (str, optional): The URL for the bot's site
        whitelist (str, optional): Comma-separated list of keywords to add to the existing whitelist
        blacklist (str, optional): Comma-separated list of words to add to the existing blacklist

    Returns:
        JSON: A response containing:
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
    with Session() as session:
        try:
            # bot = session.query(Bot).get(bot_id)
            # Explicitly join with Category to ensure it's loaded
            bot = session.query(Bot).options(joinedload(Bot.category)).get(bot_id)
            if not bot:
                return jsonify(create_response(error=f'Bot with ID {bot_id} not found')), 404

            data = request.json
            if not data:
                return jsonify(create_response(error='No update data provided')), 400

            # Update fields if provided
            updatable_fields = ['name', 'alias', 'category_id', 'dalle_prompt', 'prompt', 'background_color', 'run_frequency']
            for field in updatable_fields:
                if field in data:
                    setattr(bot, field, data[field])

            # Update icon if alias is provided
            if 'alias' in data:
                icon_normalized = data["alias"].strip().replace(" ", "_").lower()
                bot.icon = f'https://aialphaicons.s3.us-east-2.amazonaws.com/{icon_normalized}.svg'

            # Update or create Site if URL is provided
            if 'url' in data:
                if not validate_url(data['url']):
                    return jsonify(create_response(error='Invalid URL provided')), 400
                site = session.query(Site).filter_by(bot_id=bot.id).first()
                site_name_match = re.search(r"https://www\.([^.]+)\.com", data['url'])
                site_name = 'Google News' if not site_name_match else site_name_match.group(1)
                if site:
                    site.url = data['url']
                    site.name = site_name
                else:
                    new_site = Site(
                        name=site_name,
                        url=data['url'],
                        bot_id=bot.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_site)

            # Update keywords (whitelist)
            if 'whitelist' in data:
                existing_keywords = set(k.name for k in bot.keywords)
                new_keywords = set(keyword.strip().lower() for keyword in data['whitelist'].split(',') if keyword.strip())
                keywords_to_add = new_keywords - existing_keywords
                for keyword in keywords_to_add:
                    new_keyword = Keyword(name=keyword, bot_id=bot.id)
                    session.add(new_keyword)

            # Update blacklist
            if 'blacklist' in data:
                existing_blacklist = set(b.name for b in bot.blacklist)
                new_blacklist = set(word.strip().lower() for word in data['blacklist'].split(',') if word.strip())
                blacklist_to_add = new_blacklist - existing_blacklist
                for word in blacklist_to_add:
                    new_blacklist_entry = Blacklist(name=word, bot_id=bot.id)
                    session.add(new_blacklist_entry)

            bot.updated_at = datetime.now()
            session.commit()

            # Reschedule the bot if it's active and run_frequency has changed
            schedule_message = "Bot updated successfully."
            if bot.is_active:
                # Define the fields that don't require rescheduling
                non_reschedule_fields = {'backgroundcolor', 'alias'}
                
                # Check if the request contains only non-reschedule fields
                if set(data.keys()).issubset(non_reschedule_fields):
                    schedule_message += ""
                else:
                    try:
                        schedule_bot(bot, bot.category)
                        schedule_message += " Bot rescheduled successfully."
                    except Exception as e:
                        schedule_message += f" Bot rescheduling failed: {str(e)}"

            return jsonify(create_response(
                success=True,
                data=bot.as_dict(),
                message=schedule_message
            )), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f"Database error occurred: {str(e)}")), 500
        except Exception as e:
            return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), 500


@bots_bp.route('/bot/<int:bot_id>', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_all_bots','get_bot'])
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

    with Session() as session:
        try:
            bot = session.query(Bot).get(bot_id)
            if not bot:
                response["error"] = f"No bot found with ID: {bot_id}"
                return jsonify(response), 404

            # Remove scheduled job if exists
            bot_job = scheduler.get_job(id=str(bot.name))  
            if bot_job:
                scheduler.remove_job(id=str(bot.name)) 
          
            # Delete bot from database
            session.delete(bot)
            session.commit()

            response["success"] = True
            response["message"] = f"Bot with ID {bot_id} and all its associated data have been successfully deleted"
           
            return jsonify(response), 200

        except SQLAlchemyError as e:
            session.rollback()
            error_msg = f"Error occurred while deleting bot {bot_id}: {str(e)}"
            response["error"] = error_msg
            return jsonify(response), 500

        except Exception as e:
            session.rollback()
            error_msg = f"Unexpected error occurred while deleting bot {bot_id}: {str(e)}"
            response["error"] = error_msg
            return jsonify(response), 500



@bots_bp.route('/bot/<int:bot_id>/toggle-activation', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_all_bots','get_bot'])
def toggle_activation_bot(bot_id):
    with Session() as session:
        try:
            bot = session.query(Bot).get(bot_id)
            if not bot:
                return jsonify(create_response(error=f"No bot found with ID: {bot_id}")), 404
            
            category = session.query(Category).filter_by(id=bot.category_id).first()

            if bot.is_active:
                try:
                    job = scheduler.get_job(str(bot.name))
                    if job:
                        scheduler.remove_job(str(bot.name))
                    
                    bot.is_active = False
                    bot.status = 'IDLE'
                    bot.next_run_time = None
                    message = f"Bot {bot.name} deactivated successfully"
                except Exception as e:
                    return jsonify(create_response(error=f"Failed to deactivate bot: {str(e)}")), 500
            else:
                validation_errors = validate_bot_for_activation(bot, category)
                
                if validation_errors:
                    return jsonify(create_response(
                        success=False,
                        error="Bot activation failed due to the following issues:",
                        validation_errors=validation_errors
                    )), 400

                try:
                    scheduling_success = schedule_bot(bot, category)
                
                    if scheduling_success:
                        bot.is_active = True
                        bot.status = 'IDLE'
                        message = f"Bot {bot.name} scheduled and activated successfully"
                    else:
                        return jsonify(create_response(error="Failed to schedule bot")), 500
                except Exception as e:
                    return jsonify(create_response(error=f"Failed to schedule bot: {str(e)}")), 500

            bot.updated_at = datetime.now()
            session.commit()

            return jsonify(create_response(
                success=True,
                message=message,
                bot=bot.as_dict()
            )), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f"A database error occurred: {str(e)}")), 500
        except Exception as e:
            session.rollback()
            return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), 500




@bots_bp.route('/bot/metrics/download/<int:bot_id>', methods=['GET'])
def download_metrics(bot_id):
    """
    Download metrics for a specific bot in CSV or JSON format.

    Args:
        bot_id (int): The ID of the bot to retrieve metrics for.

    Returns:
        Response: A downloadable file containing the metrics data.
        HTTP Status Code:
            - 200: Metrics downloaded successfully
            - 404: Metrics not found for the specified bot
            - 500: Internal server error
    """
    try:
        metrics = Metrics.query.filter_by(bot_id=bot_id).all()
        if not metrics:
            return jsonify(create_response(error="Metrics not found for this bot")), 404

        # Determine the desired format from query parameters
        format_type = request.args.get('format', 'json').lower()

        if format_type == 'csv':
            # Convert metrics to CSV format
            output = Response(content_type='text/csv')
            output.headers["Content-Disposition"] = f"attachment; filename=metrics_bot_{bot_id}.csv"
            writer = csv.writer(output)
            writer.writerow(['Total Articles Processed', 'Articles Saved', 'Articles Discarded', 'Save Rate', 'Average Processing Time', 'Created At'])

            for metric in metrics:
                writer.writerow([
                    metric.total_articles_processed,
                    metric.articles_saved,
                    metric.articles_discarded,
                    metric.save_rate,
                    metric.average_processing_time,
                    metric.created_at
                ])
            return output

        elif format_type == 'json':
            # Convert metrics to JSON format
            metrics_data = [
                {
                    "total_articles_processed": metric.total_articles_processed,
                    "articles_saved": metric.articles_saved,
                    "articles_discarded": metric.articles_discarded,
                    "save_rate": metric.save_rate,
                    "average_processing_time": metric.average_processing_time,
                    "created_at": metric.created_at.isoformat()  # Convert datetime to string
                }
                for metric in metrics
            ]
            return jsonify(create_response(success=True, data=metrics_data)), 200

        else:
            return jsonify(create_response(error="Invalid format specified. Use 'csv' or 'json'.")), 400

    except Exception as e:
        return jsonify(create_response(error=f"An error occurred: {str(e)}")), 500
    

@bots_bp.route('/bot/metrics/<int:bot_id>', methods=['GET'])
def get_metrics(bot_id):
    """
    Get metrics for the ETL process for a specific bot.

    Args:
        bot_id (int): The ID of the bot to retrieve metrics for.

    Returns:
        JSON: A response containing the metrics data.
        HTTP Status Code:
            - 200: Metrics retrieved successfully
            - 404: Bot not found
            - 500: Internal server error
    """
    try:
        metrics = Metrics.query.filter_by(bot_id=bot_id).first()
        if not metrics:
            return jsonify(create_response(error="Metrics not found for this bot")), 404
        
        # Extract date range parameters from the request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Query metrics based on the date range
        query = Metrics.query.filter_by(bot_id=bot_id)
        if start_date:
            query = query.filter(Metrics.created_at >= start_date)
        if end_date:
            query = query.filter(Metrics.created_at <= end_date)
        
        metrics = query.first()
        if not metrics:
            return jsonify(create_response(error="Metrics not found for this bot")), 404
        
        return jsonify(create_response(success=True, data=metrics.as_dict())), 200
    except Exception as e:
        return jsonify(create_response(error=f"Failed to retrieve metrics: {str(e)}")), 500


@bots_bp.route('/api/global-metrics', methods=['GET'])
def get_global_metrics():
    """
    Get aggregated metrics across all bots with optional date range filtering.

    Returns:
        JSON: A response containing global metrics data.
        HTTP Status Code:
            - 200: Metrics retrieved successfully
            - 500: Internal server error
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        # Initialize metrics
        total_active_bots = Bot.query.filter_by(is_active=True).count()

        # Query metrics with date range filtering
        metrics_query = Metrics.query
        if start_date:
            metrics_query = metrics_query.filter(Metrics.created_at >= start_date)
        if end_date:
            metrics_query = metrics_query.filter(Metrics.created_at <= end_date)

        total_articles_processed = metrics_query.with_entities(func.sum(Metrics.total_articles_processed)).scalar() or 0
        total_articles_saved = metrics_query.with_entities(func.sum(Metrics.articles_saved)).scalar() or 0
        total_articles_discarded = metrics_query.with_entities(func.sum(Metrics.articles_discarded)).scalar() or 0

        # Calculate overall save rate
        overall_save_rate = (total_articles_saved / total_articles_processed * 100) if total_articles_processed > 0 else 0

        # Get keyword match rates
        keyword_match_rates = metrics_query.with_entities(Metrics.keyword_match_rates).all()
        aggregated_keyword_rates = {}
        for rate in keyword_match_rates:
            for keyword, value in rate.items():
                if keyword in aggregated_keyword_rates:
                    aggregated_keyword_rates[keyword] += value
                else:
                    aggregated_keyword_rates[keyword] = value

        # Get top-performing bots based on articles processed
        top_bots = db.session.query(Bot, func.sum(Metrics.total_articles_processed).label('total_processed')) \
            .join(Metrics) \
            .filter(Metrics.created_at >= start_date if start_date else True) \
            .filter(Metrics.created_at <= end_date if end_date else True) \
            .group_by(Bot.id) \
            .order_by(func.sum(Metrics.total_articles_processed).desc()) \
            .limit(5) \
            .all()

        top_performing_bots = [{ 'bot_id': bot.id, 'bot_name': bot.name, 'total_processed': total_processed } for bot, total_processed in top_bots]

        # Prepare response data
        response_data = {
            "total_active_bots": total_active_bots,
            "total_articles_processed": total_articles_processed,
            "total_articles_saved": total_articles_saved,
            "total_articles_discarded": total_articles_discarded,
            "overall_save_rate": overall_save_rate,
            "keyword_match_rates": aggregated_keyword_rates,
            "top_performing_bots": top_performing_bots
        }

        return jsonify(create_response(success=True, data=response_data)), 200

    except Exception as e:
        return jsonify(create_response(error=f"An error occurred: {str(e)}")), 500


@bots_bp.route('/api/global-metrics/download', methods=['GET'])
def download_global_metrics():
    """
    Download aggregated metrics across all bots in CSV or JSON format.

    Returns:
        Response: A downloadable file containing the global metrics data.
        HTTP Status Code:
            - 200: Metrics downloaded successfully
            - 500: Internal server error
    """

    
    # Assume we have the response_data prepared as in get_global_metrics
    response_data = get_global_metrics_data()  # This function should return the aggregated metrics data

    format_type = request.args.get('format', 'json').lower()

    if format_type == 'csv':
        output = Response(content_type='text/csv')
        output.headers["Content-Disposition"] = "attachment; filename=global_metrics.csv"
        writer = csv.writer(output)
        writer.writerow(['Total Active Bots', 'Total Articles Processed', 'Total Articles Saved', 'Total Articles Discarded', 'Overall Save Rate', 'Keyword Match Rates', 'Top Performing Bots'])

        # Write the aggregated metrics data
        writer.writerow([
            response_data['total_active_bots'],
            response_data['total_articles_processed'],
            response_data['total_articles_saved'],
            response_data['total_articles_discarded'],
            response_data['overall_save_rate'],
            json.dumps(response_data['keyword_match_rates']),  # Convert dict to JSON string
            json.dumps(response_data['top_performing_bots'])  # Convert list to JSON string
        ])
        return output

    elif format_type == 'json':
        return jsonify(create_response(success=True, data=response_data)), 200

    else:
        return jsonify(create_response(error="Invalid format specified. Use 'csv' or 'json'.")), 400


def get_global_metrics_data(start_date=None, end_date=None):
    """
    Obtener métricas agregadas a través de todos los bots con filtrado opcional por rango de fechas.

    Args:
        start_date (str): Fecha de inicio para filtrar métricas (opcional).
        end_date (str): Fecha de fin para filtrar métricas (opcional).

    Returns:
        dict: Un diccionario con los datos de métricas globales.
    """
    try:
        # Inicializar métricas
        total_active_bots = Bot.query.filter_by(is_active=True).count()

        # Consultar métricas con filtrado por rango de fechas
        metrics_query = Metrics.query
        if start_date:
            metrics_query = metrics_query.filter(Metrics.created_at >= start_date)
        if end_date:
            metrics_query = metrics_query.filter(Metrics.created_at <= end_date)

        total_articles_processed = metrics_query.with_entities(func.sum(Metrics.total_articles_processed)).scalar() or 0
        total_articles_saved = metrics_query.with_entities(func.sum(Metrics.articles_saved)).scalar() or 0
        total_articles_discarded = metrics_query.with_entities(func.sum(Metrics.articles_discarded)).scalar() or 0

        # Calcular la tasa de guardado general
        overall_save_rate = (total_articles_saved / total_articles_processed * 100) if total_articles_processed > 0 else 0

        # Obtener tasas de coincidencia de palabras clave
        keyword_match_rates = metrics_query.with_entities(Metrics.keyword_match_rates).all()
        aggregated_keyword_rates = {}
        for rate in keyword_match_rates:
            for keyword, value in rate.items():
                if keyword in aggregated_keyword_rates:
                    aggregated_keyword_rates[keyword] += value
                else:
                    aggregated_keyword_rates[keyword] = value

        # Obtener los mejores bots en función de los artículos procesados
        top_bots = db.session.query(Bot, func.sum(Metrics.total_articles_processed).label('total_processed')) \
            .join(Metrics) \
            .filter(Metrics.created_at >= start_date if start_date else True) \
            .filter(Metrics.created_at <= end_date if end_date else True) \
            .group_by(Bot.id) \
            .order_by(func.sum(Metrics.total_articles_processed).desc()) \
            .limit(5) \
            .all()

        top_performing_bots = [{'bot_id': bot.id, 'bot_name': bot.name, 'total_processed': total_processed} for bot, total_processed in top_bots]

        # Preparar los datos de respuesta
        response_data = {
            "total_active_bots": total_active_bots,
            "total_articles_processed": total_articles_processed,
            "total_articles_saved": total_articles_saved,
            "total_articles_discarded": total_articles_discarded,
            "overall_save_rate": overall_save_rate,
            "keyword_match_rates": aggregated_keyword_rates,
            "top_performing_bots": top_performing_bots
        }

        return response_data

    except Exception as e:
        raise Exception(f"An error occurred while retrieving global metrics: {str(e)}")