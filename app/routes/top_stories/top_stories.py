from app.routes.routes_utils import create_response
from flask import request, Blueprint, jsonify
from sqlalchemy.orm.exc import NoResultFound
from config import db, Article, ArticleTimeframe
from http import HTTPStatus
from sqlalchemy import desc
from datetime import datetime

from flask import Blueprint, jsonify, request
from config import Article, db
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from app.services.slack.actions import send_WARNING_message_to_slack_channel
import json
import re


top_stories_bp = Blueprint(
    'top_stories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@top_stories_bp.route('/top-stories/<int:article_id>', methods=['POST'])
@handle_db_session
def set_top_story(article_id):
    """
    Set an article as a top story and assign timeframes.

    This endpoint takes an article ID as a URL parameter, sets its is_top_story field to True,
    and associates it with the provided timeframes.

    URL Parameters:
        article_id (int): The ID of the article to be set as a top story

    Request Body:
        timeframes (list): List of timeframes to associate with the article ('1D', '1W', '1M')

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - message (str): A message describing the result of the operation
            - data (dict): The updated article information
            - error (str or None): Error message, if any
    """
    try:
        data = request.get_json()
        timeframes = data.get('timeframes', []) if data else []

        # Validate timeframes
        valid_timeframes = ['1D', '1W', '1M']
        if not timeframes:
            return jsonify(create_response(
                error="At least one timeframe must be provided"
            )), HTTPStatus.BAD_REQUEST

        invalid_timeframes = [tf for tf in timeframes if tf not in valid_timeframes]
        if invalid_timeframes:
            return jsonify(create_response(
                error=f"Invalid timeframes: {', '.join(invalid_timeframes)}. Must be one of: {', '.join(valid_timeframes)}"
            )), HTTPStatus.BAD_REQUEST

        article = Article.query.get(article_id)
        if not article:
            return jsonify(create_response(
                error=f"Article with ID {article_id} not found"
            )), HTTPStatus.NOT_FOUND

        # Set article as top story
        article.is_top_story = True
        article.updated_at = datetime.now()

        # Add timeframes
        current_time = datetime.now()
        for timeframe in timeframes:
            new_timeframe = ArticleTimeframe(
                timeframe=timeframe,
                created_at=current_time,
                updated_at=current_time
            )
            article.timeframes.append(new_timeframe)

        db.session.commit()

        return jsonify(create_response(
            success=True,
            message=f"Article {article_id} has been set as a top story with timeframes: {', '.join(timeframes)}",
            data=article.as_dict()
        )), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        return jsonify(create_response(
            error=f"An unexpected error occurred: {str(e)}"
        )), HTTPStatus.INTERNAL_SERVER_ERROR
    
    
@top_stories_bp.route('/top-stories', methods=['GET'])
def get_top_stories():
    """
    Retrieve top stories from the article database with optional pagination, timeframe filtering,
    and bot filtering.

    Query Parameters:
        page (int, optional): The page number for pagination (default: 1)
        per_page (int, optional): The number of items per page for pagination (default: 10)
        timeframe (str, optional): Filter by timeframe ('1D', '1W', '1M')
        bot_id (str, optional): Comma-separated bot IDs to filter by
                              Example: /top-stories?bot_id=1,2,3
                              If not provided, returns stories from all bots

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (dict): Dictionary of articles grouped by bot_id (includes empty arrays for specified bots with no stories)
            - count (int): Total number of articles returned
            - total (int): Total number of top stories
            - page (int): Current page number
            - pages (int): Total number of pages
            - error (str or None): Error message, if any
    """
    try:
        # Get query parameters with defaults
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=10)
        timeframe = request.args.get('timeframe')
        bot_ids_param = request.args.get('bot_id')

        # Validate pagination parameters
        if page < 1:
            return jsonify(create_response(
                error="Page number must be greater than 0"
            )), HTTPStatus.BAD_REQUEST
        
        if per_page < 1:
            return jsonify(create_response(
                error="Items per page must be greater than 0"
            )), HTTPStatus.BAD_REQUEST

        # Process comma-separated bot_ids if provided
        bot_ids = None
        if bot_ids_param:
            try:
                bot_ids = [int(id_.strip()) for id_ in bot_ids_param.split(',')]
            except ValueError:
                return jsonify(create_response(
                    error="Invalid bot_id format. Must be comma-separated integers (e.g., 1,2,3)"
                )), HTTPStatus.BAD_REQUEST
        # Validate timeframe if provided
        valid_timeframes = ['1D', '1W', '1M']
        if timeframe:
            normalized_timeframe = timeframe.upper()
            if normalized_timeframe not in valid_timeframes:
                return jsonify(create_response(
                    error=f"Invalid timeframe: {timeframe}. Must be one of: {', '.join(valid_timeframes)}"
                )), HTTPStatus.BAD_REQUEST
            timeframe = normalized_timeframe
        
        # Build query
        query = Article.query.filter_by(is_top_story=True)
        
        if bot_ids:
            query = query.filter(Article.bot_id.in_(bot_ids))

        if timeframe:
            query = query.join(Article.timeframes).filter(ArticleTimeframe.timeframe == timeframe)
        
        query = query.order_by(desc(Article.date))
        
        # Always use pagination with defaults
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        articles = pagination.items

        # Convert articles to array of dictionaries
        articles_array = [article.as_dict() for article in articles]
        
        return jsonify(create_response(
            success=True,
            data=articles_array,
            count=len(articles),
            total=pagination.total,
            page=page,
            pages=pagination.pages,
            per_page=per_page,
            timeframe=timeframe,
            queried_bots=bot_ids  # Will be None if no bot_ids were specified
        )), HTTPStatus.OK

    except Exception as e:
        return jsonify(create_response(
            error=f"An unexpected error occurred: {str(e)}"
        )), HTTPStatus.INTERNAL_SERVER_ERROR


@top_stories_bp.route('/top-story/<int:article_id>', methods=['GET'])
def get_top_story_by_id(article_id):
    """
    Retrieve a single top story article by its ID.

    This endpoint queries the database for a specific article that is marked as a top story
    and has the given ID.

    Args:
        article_id (int): The ID of the article to retrieve.

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (dict or None): Details of the top story article, if found
            - error (str or None): Error message, if any
        HTTP Status Code

    Raises:
        404 Not Found: If no top story article with the given ID is found
        400 Bad Request: If the provided article_id is not a valid integer
        500 Internal Server Error: If there's an unexpected error during execution
    """
    try:
        # Query the database for the top story with the given ID
        article = Article.query.filter_by(id=article_id, is_top_story=True).one()
        
        return jsonify(create_response(
            success=True,
            data=article.as_dict()
        )), HTTPStatus.OK

    except NoResultFound:
        return jsonify(create_response(
            error=f"No top story found with ID: {article_id}"
        )), HTTPStatus.NOT_FOUND
    
    except ValueError as ve:
        return jsonify(create_response(
            error=f"Invalid input: {str(ve)}"
        )), HTTPStatus.BAD_REQUEST
    
    except Exception as e:
        return jsonify(create_response(
            error=f"An unexpected error occurred: {str(e)}"
        )), HTTPStatus.INTERNAL_SERVER_ERROR


@top_stories_bp.route('/top-story/<int:article_id>', methods=['PATCH'])
@handle_db_session
def remove_top_story(article_id):
    """
    Remove an article from top stories by setting its is_top_story flag to False
    and removing its associated timeframes.

    This endpoint updates a specific article in the database, changing its is_top_story
    status to False and removing all associated timeframes.

    Args:
        article_id (int): The ID of the article to remove from top stories.

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (dict): Contains the ID of the updated article
            - message (str): A success message
            - error (str or None): Error message, if any
        HTTP Status Code

    Raises:
        404 Not Found: If no article with the given ID is found
        400 Bad Request: If the provided article_id is not a valid integer
        500 Internal Server Error: If there's an unexpected error during execution
    """
    try:
        # Query the database for the article with the given ID
        article = Article.query.filter_by(id=article_id, is_top_story=True).first()
        
        if article is None:
            return jsonify(create_response(
                error=f"No top story found with ID: {article_id}"
            )), HTTPStatus.NOT_FOUND
        
        # Remove all timeframes associated with the article
        ArticleTimeframe.query.filter_by(article_id=article_id).delete()
        
        # Update the is_top_story flag
        article.is_top_story = False
        article.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify(create_response(
            success=True,
            data={'updated_id': article_id},
            message=f"Article with ID {article_id} has been removed from top stories"
        )), HTTPStatus.OK

    except ValueError as ve:
        db.session.rollback()
        return jsonify(create_response(
            error=f"Invalid input: {str(ve)}"
        )), HTTPStatus.BAD_REQUEST
    
    except Exception as e:
        db.session.rollback()
        return jsonify(create_response(
            error=f"An unexpected error occurred: {str(e)}"
        )), HTTPStatus.INTERNAL_SERVER_ERROR
