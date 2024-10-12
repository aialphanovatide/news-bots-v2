# routes.py
import os
import boto3
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request, current_app
from config import Bot, Category, db, Session
from app.routes.routes_utils import create_response
from scheduler_config import scheduler
from redis_client.redis_client import cache_with_redis, update_cache_with_redis
from app.routes.bots.utils import schedule_bot, validate_bot_for_activation

load_dotenv()

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


@categories_bp.route('/category', methods=['POST'])
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
            
            # Normalize icon name
            icon_normalized = data["alias"].strip().replace(" ", "_").lower()

            # Create new category
            current_time = datetime.now()
            new_category = Category(
                name=data['name'],
                alias=data['alias'],
                slack_channel=data.get('slack_channel', ''),
                border_color=data.get('border_color', ''),
                icon=f'https://aialphaicons.s3.us-east-2.amazonaws.com/{icon_normalized}.svg',
                is_active=False,
                created_at=current_time,
                updated_at=current_time 
            )

            session.add(new_category)
            session.commit()

            return jsonify({'success': True, 'data': new_category.as_dict()}), 201

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500

        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500


           
@categories_bp.route('/category/<int:category_id>', methods=['DELETE'])
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
    Get all available categories along with their associated bots (basic info only).
    Response:
        200: Successfully retrieved categories with their bots.
        404: No categories found.
        500: Internal server error or database error.
    """
    with Session() as session:
        try:
            # Load all categories with their related bots
            categories = session.query(Category).options(
                joinedload(Category.bots)
            ).all()

            if not categories:
                return jsonify(create_response(error='No categories found')), 404

            categories_data = []
            for category in categories:
                category_dict = category.as_dict()
                category_dict['bots'] = [bot.as_dict() for bot in category.bots]
                categories_data.append(category_dict)

            return jsonify(create_response(success=True, data={'categories': categories_data})), 200

        except SQLAlchemyError as e:
            session.rollback()
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

            query = session.query(Category).options(joinedload(Category.bots))
            if category_id:
                query = query.filter(Category.id == category_id)
            elif category_name:
                query = query.filter(Category.name == category_name)

            category = query.first()

            if not category:
                return jsonify(create_response(error='Category not found.')), 404

            category_data = category.as_dict()
            category_data['bots'] = [bot.as_dict() for bot in category.bots]

            return jsonify(create_response(success=True, data={'category': category_data})), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f'Database error: {str(e)}')), 500

        except Exception as e:
            return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500



@categories_bp.route('/category/<int:category_id>', methods=['PUT'])
@update_cache_with_redis(related_get_endpoints=['get_categories','get_category','get_articles_by_bot'])
def update_category(category_id):
    with Session() as session:
        try:
            category = session.query(Category).get(category_id)
            if not category:
                return jsonify(create_response(error=f'Category with ID {category_id} not found')), 404

            data = request.json
            if not data:
                return jsonify(create_response(error='No update data provided')), 400
            
            allowed_fields = ['name', 'alias', 'slack_channel', 'border_color']
            for field in allowed_fields:
                if field in data:
                    setattr(category, field, data[field])

            # Update icon if alias is provided
            if 'alias' in data:
                icon_normalized = data["alias"].strip().replace(" ", "_").lower()
                category.icon = f'https://aialphaicons.s3.us-east-2.amazonaws.com/{icon_normalized}.svg'

            category.updated_at = datetime.now()

            rescheduled_bots = []
            failed_reschedules = []
            if any(field in allowed_fields for field in ['name', 'alias', 'slack_channel']):
                active_bots = [bot for bot in category.bots if bot.is_active]
                for bot in active_bots:
                    try:
                        scheduling_success = schedule_bot(bot, category)
                        if scheduling_success:
                            rescheduled_bots.append(bot.name)
                        else:
                            failed_reschedules.append(bot.name)
                    except Exception as e:
                        current_app.logger.exception(f"Error rescheduling bot {bot.name}: {str(e)}")
                        failed_reschedules.append(bot.name)

            session.commit()

            message = "Category updated successfully."
            if allowed_fields:
                message += f" Updated fields: {', '.join(allowed_fields)}."
            if rescheduled_bots:
                message += f" Rescheduled bots: {', '.join(rescheduled_bots)}."
            if failed_reschedules:
                message += f" Failed to reschedule bots: {', '.join(failed_reschedules)}."

            return jsonify(create_response(
                success=True, 
                message=message,
                data={
                    'category': category.as_dict(),
                    'rescheduled_bots': rescheduled_bots,
                    'failed_reschedules': failed_reschedules
                }
            )), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f'Database error: {str(e)}')), 500

        except Exception as e:
            session.rollback()
            return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500



@categories_bp.route('/category/<int:category_id>/toggle-activation', methods=['POST'])
@update_cache_with_redis(related_get_endpoints=['get_categories', 'get_category', 'get_articles_by_bot'])
def toggle_category_activation(category_id):
    """
    Toggle activation for all bots within a specific category.

    Args:
        category_id (int): The ID of the category to process.

    Returns:
        JSON: A response detailing the status of each processed bot.
    """
    with Session() as session:
        try:
            category = session.query(Category).get(category_id)
            if not category:
                return jsonify(create_response(error=f'Category with ID {category_id} not found')), 404

            bots = session.query(Bot).filter_by(category_id=category_id).all()
            if not bots:
                return jsonify(create_response(success=True, message='No bots found in this category')), 200

            success_count = 0
            failure_count = 0
            processed_bots = []

            for bot in bots:
                bot_result = {
                    'id': bot.id,
                    'name': bot.name,
                    'previous_state': 'active' if bot.is_active else 'inactive',
                    'new_state': None,
                    'status': None,
                    'error': None
                }

                try:
                    if not bot.is_active:
                        # Activation logic
                        bot_validation_errors = validate_bot_for_activation(bot, category)
                        if bot_validation_errors:
                            bot_result['status'] = 'failed'
                            bot_result['error'] = f"Validation errors: {bot_validation_errors}"
                            failure_count += 1
                        else:
                            scheduling_success = schedule_bot(bot, category)
                            if scheduling_success:
                                bot.is_active = True
                                bot.status = 'IDLE'
                                bot_result['new_state'] = 'active'
                                bot_result['status'] = 'success'
                                success_count += 1
                            else:
                                bot_result['status'] = 'failed'
                                bot_result['error'] = "Failed to schedule bot"
                                failure_count += 1
                    else:
                        # Deactivation logic
                        job = scheduler.get_job(str(bot.name))
                        if job:
                            scheduler.remove_job(str(bot.name))
                        bot.is_active = False
                        bot.status = 'IDLE'
                        bot.next_run_time = None
                        bot_result['new_state'] = 'inactive'
                        bot_result['status'] = 'success'
                        success_count += 1

                    bot.updated_at = datetime.now()
                    session.commit()

                except Exception as e:
                    session.rollback()
                    bot_result['status'] = 'failed'
                    bot_result['error'] = str(e)
                    failure_count += 1
                    current_app.logger.exception(f'Error processing bot {bot.id}: {str(e)}')

                processed_bots.append(bot_result)

            activated_count = sum(1 for bot in processed_bots if bot['new_state'] == 'active')
            deactivated_count = sum(1 for bot in processed_bots if bot['new_state'] == 'inactive')

            summary = {
                'total_bots': len(bots),
                'activated_count': activated_count,
                'deactivated_count': deactivated_count,
                'success_count': success_count,
                'failure_count': failure_count,
                'processed_bots': processed_bots
            }

            return jsonify(create_response(
                success=True,
                message=f'Operation completed. {activated_count} bots activated, {deactivated_count} bots deactivated.',
                data=summary
            )), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify(create_response(error=f'Database error: {str(e)}')), 500

        except Exception as e:
            session.rollback()
            return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500