# routes.py
from datetime import datetime, timedelta
import os
from flask import Blueprint, jsonify, request
from app.routes.bots.activate import scheduled_job
from config import Blacklist, Bot, Category, Site, db, Session
from dotenv import load_dotenv
import boto3
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response
from redis_client.redis_client import cache_with_redis, update_cache_with_redis
from scheduler_config import reschedule, scheduler


load_dotenv()

SERVER_LINK = os.getenv('SERVER_LINK')
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')


categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

s3 = boto3.client(
    's3',
    region_name='us-east-2',
    aws_access_key_id=AWS_ACCESS,
    aws_secret_access_key=AWS_SECRET_KEY
)


@categories_bp.route('/categories', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def create_category():
    """
    Create a new category on the news bot server.

    Request JSON:
        name (str): Required. The name of the category.
        alias (str): Required. The alias of the category.
        prompt (str): Optional. The prompt for the category.
        slack_channel (str): Optional. The Slack channel associated with the category.
        border_color (str): Optional. The HEX code for the border color.
        icon (file): Optional. An SVG file for the category icon.

    Returns:
        JSON: A response with the created category data or an error message.
    """
    with Session() as session:
        try:
            data = request.json 
            # Validate required fields
            if not data.get('name') or not data.get('alias'):
                return jsonify({'error': 'Name and alias are required'}), 400

            # Check if the category already exists
            existing_category = session.query(Category).filter_by(name=data['name']).first()
            if existing_category:
                return jsonify({'error': f'Category {data["name"]} already exists'}), 400

            # Handle SVG icon upload
            icon_url = None
            if 'icon' in request.files:
                icon_file = request.files['icon']
                if icon_file.filename.lower().endswith('.svg'):
                    alias_normalized = data['alias'].strip().replace(" ", "_")
                    icon_filename = f"{alias_normalized}.svg"
                    s3.upload_fileobj(
                        icon_file, 
                        'aialphaicons', 
                        icon_filename,
                        ExtraArgs={"ContentType": "image/svg+xml"}
                    )
                    icon_url = f'https://aialphaicons.s3.amazonaws.com/{icon_filename}'
                else:
                    return jsonify({'error': 'Invalid file type. Only SVG files are allowed.'}), 400

            # Create new category
            current_time = datetime.now()
            new_category = Category(
                name=data['name'],
                alias=data['alias'],
                prompt=data.get('prompt', ''),
                slack_channel=data.get('slack_channel', ''),
                border_color=data.get('border_color', ''),
                icon=icon_url,
                is_active=False,
                created_at=current_time,
                updated_at=current_time  # Assign the same value for updated_at
            )

            session.add(new_category)
            session.commit()

            return jsonify({'success': True, 'data': new_category.as_dict()}), 201

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

           
@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def delete_category(category_id):
    """
    Delete a category and its associated bots by ID.

    Args:
        category_id (int): ID of the category to delete.

    Returns:
        JSON: A response indicating success or failure.
    """
    with Session() as session:
        try:
            # Fetch the category to delete
            category = session.query(Category).get(category_id)
            if not category:
                return jsonify({'error': f'Category with ID {category_id} not found'}), 404

            # Delete associated SVG icon from S3
            if category.icon:
                icon_filename = category.icon.split('/')[-1]
                s3.delete_object(Bucket='aialphaicons', Key=icon_filename)

            # Delete the category (cascades to bots and related entries)
            session.delete(category)

            # Commit the transaction
            session.commit()

            return jsonify({'success': True, 'data': {'deleted_id': category_id}}), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500



@categories_bp.route('/categories', methods=['GET'])
@cache_with_redis()
def get_categories():
    """
    Get all available categories along with their associated bots and bot details.
    Response:
        200: Successfully retrieved categories with their bots.
        404: No categories found.
        500: Internal server error or database error.
    """
    with Session() as session:
        try:
            # Cargar todas las categorías con sus bots relacionados
            categories = Category.query.options(db.joinedload(Category.bots)).all()

            if not categories:
                return jsonify(create_response(error='No categories found')), 404

            categories_with_bots = [
                {
                    'id': category.id,
                    'name': category.name,
                    'alias': category.alias,
                    'prompt': category.prompt,
                    'slack_channel': category.slack_channel,
                    'icon': category.icon,
                    'is_active': category.is_active,
                    'border_color': category.border_color,
                    'updated_at': category.updated_at,
                    'created_at': category.created_at,
                    'bots': [
                        {
                            'id': bot.id,
                            'name': bot.name,
                            'dalle_prompt': bot.dalle_prompt,
                            'created_at': bot.created_at,
                            'updated_at': bot.updated_at,
                            'sites': [site.as_dict() for site in bot.sites],
                            'keywords': [keyword.as_dict() for keyword in bot.keywords],
                            'blacklist': [blacklist.as_dict() for blacklist in bot.blacklist],
                            'articles': [article.as_dict() for article in bot.articles],
                            'unwanted_articles': [unwanted_article.as_dict() for unwanted_article in bot.unwanted_articles],
                        } for bot in category.bots
                    ]
                } for category in categories
            ]
            return jsonify(create_response(success=True, data={'categories': categories_with_bots})), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(create_response(error=f'Database error: {str(e)}')), 500

        except Exception as e:
            return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500
        
        
@categories_bp.route('/category', methods=['GET'])
@cache_with_redis()
def get_category():
    """
    Get a category by id or name.
    Query Params:
        category_id (int): The ID of the category.
        category_name (str): The name of the category.
    Response:
        200: Successfully retrieved the category.
        400: Bad request, no valid parameters provided.
        404: Category not found.
        500: Internal server error or database error.
    """
    category_id = request.args.get('category_id', type=int)
    category_name = request.args.get('category_name', type=str)
    
    with Session() as session:
        try:
            if not category_id and not category_name:
                return jsonify(create_response(error='You must provide either category_id or category_name.')), 400

            query = Category.query
            if category_id:
                query = query.filter_by(id=category_id)
            if category_name:
                query = query.filter_by(name=category_name)

            category = query.first()

            if not category:
                return jsonify(create_response(error='Category not found.')), 404

            category_data = {
                'category': category.name,
                'isActive': category.is_active,
                'alias': category.alias,
                'icon': category.icon,
                'updated_at': category.updated_at,
                'color': category.border_color
            }

            return jsonify(create_response(success=True, data={'category': category_data})), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(create_response(error=f'Database error: {str(e)}')), 500

        except Exception as e:
            return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def update_category(category_id):
    """
    Update an existing category by ID.

    Args:
        category_id (int): ID of the category to update.

    Request JSON:
        name (str, optional): New name for the category.
        alias (str, optional): New alias for the category.
        prompt (str, optional): New prompt for the category.
        slack_channel (str, optional): New Slack channel for the category.
        icon (file, optional): New SVG file for the category icon.
        border_color (str, optional): New HEX code for the border color.

    Returns:
        JSON: A response with the updated category data or an error message.
    """
    with Session() as session:
        try:
            data = request.form.to_dict()  # To support form-data for icon upload
            # Fetch the category to update
            category = session.query(Category).get(category_id)
            if not category:
                return jsonify({'error': f'Category with ID {category_id} not found'}), 404

            # Update category fields (only allow specific fields to be updated)
            allowed_fields = ['name', 'alias', 'prompt', 'slack_channel', 'border_color']
            for key, value in data.items():
                if key in allowed_fields:
                    setattr(category, key, value)

            # Handle SVG icon update
            if 'icon' in request.files:
                icon_file = request.files['icon']
                if icon_file.filename.lower().endswith('.svg'):
                    # Delete old icon if exists
                    if category.icon:
                        old_icon_filename = category.icon.split('/')[-1]
                        s3.delete_object(Bucket='aialphaicons', Key=old_icon_filename)

                    # Upload new icon
                    alias_normalized = category.alias.strip().replace(" ", "_")
                    icon_filename = f"{alias_normalized}.svg"
                    s3.upload_fileobj(
                        icon_file,
                        'aialphaicons',
                        icon_filename,
                        ExtraArgs={"ContentType": "image/svg+xml"}
                    )
                    category.icon = f'https://aialphaicons.s3.amazonaws.com/{icon_filename}'
                else:
                    return jsonify({'error': 'Invalid file type. Only SVG files are allowed.'}), 400

            # Update updated_at timestamp
            category.updated_at = datetime.now()

            # Reschedule bots if necessary
            if any(key in data for key in ['name', 'alias', 'prompt', 'slack_channel']):
                for bot in category.bots:
                    reschedule(bot.id)

            # Commit the update
            session.commit()

            return jsonify({'success': True, 'data': category.as_dict()}), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@categories_bp.route('/categories/<int:category_id>/toggle-coins', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def toggle_category_coins(category_id):
    """
    Activate or deactivate all coins within a specific category.

    Args:
        category_id (int): The ID of the category to process.

    Request JSON:
        action (str): Either "activate" or "deactivate"

    Returns:
        JSON: A response detailing the status of each processed coin bot.
    """
    with Session() as session:
        try:
            data = request.get_json()
            action = data.get('action')
            if action not in ['activate', 'deactivate']:
                return jsonify({'error': 'Invalid action. Must be "activate" or "deactivate"'}), 400

            category = session.query(Category).get(category_id)
            if not category:
                return jsonify({'error': f'Category with ID {category_id} not found'}), 404

            bots = session.query(Bot).filter_by(category_id=category_id).all()
            if not bots:
                return jsonify({'success': True, 'message': 'No bots found in this category'}), 200

            activation_success = 0
            activation_failures = 0
            failed_bot_ids = []
            last_execution_time = datetime.now()

            for bot in bots:
                if action == 'activate' and not bot.is_active:
                    site = session.query(Site).filter_by(bot_id=bot.id).first()
                    if not site or not hasattr(site, 'url') or not site.url:
                        activation_failures += 1
                        failed_bot_ids.append(bot.id)
                        continue
                    try:
                        next_execution_time = last_execution_time + timedelta(minutes=23)
                        scheduler.add_job(
                            id=str(bot.id),
                            func=scheduled_job,
                            name=bot.name,
                            replace_existing=True,
                            args=[site.url,bot.name, bot.category_id, bot.id],
                            trigger='date',
                            run_date=next_execution_time
                        )
                        
                        bot.is_active = True
                        session.commit()
                        activation_success += 1
                        last_execution_time = next_execution_time
                    except Exception as e:
                        session.rollback()
                        activation_failures += 1
                        failed_bot_ids.append(bot.id)
                        print(f'Error activating bot {bot.id}: {str(e)}')
                        
                elif action == 'deactivate' and bot.is_active:
                    try:
                        job = scheduler.get_job(id=str(bot.id))
                        if job:
                            scheduler.remove_job(id=str(bot.id))
                        
                        bot.is_active = False
                        session.commit()
                        activation_success += 1
                    except Exception as e:
                        session.rollback()
                        activation_failures += 1
                        failed_bot_ids.append(bot.id)
                        print(f'Error deactivating bot {bot.id}: {str(e)}')

            summary = {
                'total_bots': len(bots),
                'activated_count': activation_success if action == 'activate' else 0,
                'deactivated_count': activation_success if action == 'deactivate' else 0,
                'failed_count': activation_failures,
                'failed_bot_ids': failed_bot_ids
            }

            return jsonify({'success': True, 'message': 'Operation completed successfully', 'data': summary}), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500



# DEPRECATED: THIS ENDPOINT WILL BE REMOVED
@categories_bp.route('/toggle-all-coins', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def toggle_all_coins():
    """
    Toggle activation state of all coins in all categories.

    Request JSON:
        action (str): Either "activate" or "deactivate"

    Returns:
        JSON: A response detailing the status of each processed coin bot.
    """
    with Session() as session:
        try:
            data = request.get_json()
            action = data.get('action')
            if action not in ['activate', 'deactivate']:
                return jsonify({'error': 'Invalid action. Must be "activate" or "deactivate"'}), 400

            categories = session.query(Category).all()
            if not categories:
                return jsonify({'success': True, 'message': 'No categories found'}), 404

            activation_success = 0
            activation_failures = 0
            failed_bot_ids = []

            last_category_execution_time = datetime.now()

            for category in categories:
                bots = session.query(Bot).filter_by(category_id=category.id).all()
                if not bots:
                    continue

                last_bot_execution_time = last_category_execution_time

                for bot in bots:
                    if action == 'activate' and not bot.is_active:
                        try:
                            site = session.query(Site).filter_by(bot_id=bot.id).first()
                            if not site or not site.url:
                                continue

                            bot_site = site.url
                            bot_blacklist = [bl.name for bl in session.query(Blacklist).filter_by(bot_id=bot.id).all()]
                            next_execution_time = last_bot_execution_time + timedelta(minutes=23)

                            scheduler.add_job(
                                id=str(bot.id),
                                func=scheduled_job,
                                name=bot.name,
                                replace_existing=True,
                                args=[bot_site, bot.name, category.id, bot.id],
                                trigger='date',
                                run_date=next_execution_time
                            )
                            print(f"Job added for bot {bot.id}: scheduled to run at {next_execution_time}")
                            bot.is_active = True
                            session.commit()
                            activation_success += 1
                            last_bot_execution_time = next_execution_time
                        except Exception as e:
                            session.rollback()
                            activation_failures += 1
                            failed_bot_ids.append(bot.id)
                            print(f'Error activating bot {bot.id}: {str(e)}')

                    elif action == 'deactivate' and bot.is_active:
                        try:
                            job = scheduler.get_job(id=str(bot.id))
                            if job:
                                scheduler.remove_job(id=str(bot.id))
                            
                            bot.is_active = False
                            session.commit()
                            activation_success += 1
                        except Exception as e:
                            session.rollback()
                            activation_failures += 1
                            failed_bot_ids.append(bot.id)
                            print(f'Error deactivating bot {bot.id}: {str(e)}')

                last_category_execution_time = last_bot_execution_time + timedelta(minutes=5)

            summary = {
                'total_bots': len(session.query(Bot).all()),
                'activated_count': activation_success if action == 'activate' else 0,
                'deactivated_count': activation_success if action == 'deactivate' else 0,
                'failed_count': activation_failures,
                'failed_bot_ids': failed_bot_ids
            }

            return jsonify({'success': True, 'message': 'Operation completed successfully', 'data': summary}), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            session.rollback()
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
