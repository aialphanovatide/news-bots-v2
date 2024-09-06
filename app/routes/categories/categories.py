# routes.py

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import os
from flask import Blueprint, jsonify, request
import requests
from app.routes.bots.activate import scheduled_job
from app.utils.helpers import measure_execution_time
from config import Article, Blacklist, Bot, Category, Keyword, Site, UnwantedArticle, UsedKeywords, db
from dotenv import load_dotenv
import boto3
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from dotenv import load_dotenv
import os
from scheduler_config import reschedule, scheduler
from apscheduler.triggers.date import DateTrigger

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

    try:
        data = request.json
        session = db.session    
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
                icon_filename = f"{data['alias']}.svg"
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
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            prompt=data.get('prompt', ''),
            slack_channel=data.get('slack_channel', ''),
            border_color=data.get('border_color', ''),
            icon=icon_url,
            created_at=datetime.now()
        )

        session.add(new_category)
        session.commit()

        return jsonify({'success': True, 'data': new_category.as_dict()}), 201

    except SQLAlchemyError as e:
        session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    finally:
        session.close()
           
@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """
    Delete a category and its associated bots by ID.

    Args:
        category_id (int): ID of the category to delete.

    Returns:
        JSON: A response indicating success or failure.
    """
    session = db.session
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

    finally:
        session.close()


@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Get all available categories along with their associated bots and bot details.
    Response:
        200: Successfully retrieved categories with their bots.
        404: No categories found.
        500: Internal server error or database error.
    """
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
                'time_interval': category.time_interval,
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

@categories_bp.route('/get_all_bots', methods=['GET'])
def get_bots():
    """
    Get all bots.
    Response:
        200: Successfully retrieved bots.
        500: Internal server error or database error.
    """
    try:
        categories = Category.query.order_by(Category.id).all()

        bots = [
            {
                'category': category.name,
                'isActive': category.is_active,
                'alias': category.alias,
                'icon': category.icon,
                'updated_at': category.updated_at,
                'color': category.border_color
            } for category in categories
        ]
        return jsonify(create_response(success=True, data={'bots': bots})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@categories_bp.route('/categories/<int:category_id>', methods=['PUT'])
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
    session = db.session
    try:
        data = request.get_json()

        # Fetch the category to update
        category = session.query(Category).get(category_id)
        if not category:
            return jsonify({'error': f'Category with ID {category_id} not found'}), 404

        # Update category fields
        for key, value in data.items():
            if hasattr(category, key):
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
                icon_filename = f"{category.alias}.svg"
                s3.upload_fileobj(
                    icon_file,
                    'aialphaicons',
                    icon_filename,
                    ExtraArgs={"ContentType": "image/svg+xml"}
                )
                category.icon = f'https://aialphaicons.s3.amazonaws.com/{icon_filename}'
            else:
                return jsonify({'error': 'Invalid file type. Only SVG files are allowed.'}), 400

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

    finally:
        session.close()


@categories_bp.route('/categories/<int:category_id>/toggle-coins', methods=['POST'])
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
    session = db.session
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
                try:
                    next_execution_time = last_execution_time + timedelta(minutes=23)  # Intervalo de 23 minutos
                    scheduler.add_job(
                        id=str(bot.id),
                        func=scheduled_job,
                        name=bot.name,
                        replace_existing=True,
                        args=[bot.url, bot.name, [bl.name for bl in session.query(Blacklist).filter_by(bot_id=bot.id).all()], bot.category_id, bot.id, category.slack_channel],
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

    finally:
        session.close()


@categories_bp.route('/toggle-all-coins', methods=['POST'])
def toggle_all_coins():
    """
    Toggle activation state of all coins in all categories.

    Request JSON:
        action (str): Either "activate" or "deactivate"

    Returns:
        JSON: A response detailing the status of each processed coin bot.
    """
    session = db.session
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
            bots = session.query(Bot).filter_by(category_id=category.category_id).all()
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
                            args=[bot_site, bot.name, bot_blacklist, None, bot.id, None],
                            trigger='date',
                            run_date=next_execution_time
                        )
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

    finally:
        session.close()