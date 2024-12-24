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
    

# @top_stories_bp.route('/top-stories', methods=['GET'])
# def get_top_stories():
#     """
#     Retrieve top stories from the article database with optional pagination.

#     This endpoint queries the database for articles marked as top stories,
#     ordered by date (most recent first). It supports optional pagination.

#     Query Parameters:
#         page (int, optional): The page number for pagination.
#         per_page (int, optional): The number of items per page for pagination.

#     Returns:
#         JSON: A JSON object containing:
#             - success (bool): Indicates if the operation was successful
#             - data (list): List of top story articles, each as a dictionary
#             - count (int): Number of articles returned
#             - total (int): Total number of top stories (only with pagination)
#             - page (int): Current page number (only with pagination)
#             - pages (int): Total number of pages (only with pagination)
#             - error (str or None): Error message, if any
#         HTTP Status Code

#     Raises:
#         400 Bad Request: If the provided parameters are not valid
#         500 Internal Server Error: If there's an unexpected error during execution
#     """
#     try:
#         # Check if pagination is requested
#         page = request.args.get('page', type=int)
#         per_page = request.args.get('per_page', type=int)
        
#         # Query for top stories
#         query = Article.query.filter_by(is_top_story=True).order_by(desc(Article.date))
        
#         if page is not None and per_page is not None:
#             # Use pagination
#             pagination = query.paginate(page=page, per_page=per_page, error_out=False)
#             top_stories = pagination.items
#             result = [article.as_dict() for article in top_stories]
            
#             return jsonify(create_response(
#                 success=True,
#                 data=result,
#                 count=len(result),
#                 total=pagination.total,
#                 page=page,
#                 pages=pagination.pages
#             )), HTTPStatus.OK
#         else:
#             # No pagination, return all top stories
#             top_stories = query.all()
#             result = [article.as_dict() for article in top_stories]
            
#             return jsonify(create_response(
#                 success=True,
#                 data=result,
#                 count=len(result)
#             )), HTTPStatus.OK

#     except ValueError as ve:
#         return jsonify(create_response(error=f"Invalid input: {str(ve)}")), HTTPStatus.BAD_REQUEST
    
#     except Exception as e:
#         db.session.rollback()
#         return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), HTTPStatus.INTERNAL_SERVER_ERROR


@top_stories_bp.route('/top-stories', methods=['GET'])
def get_top_stories():
    """
    Retrieve top stories from the article database with optional pagination and timeframe filtering.

    This endpoint queries the database for articles marked as top stories,
    ordered by date (most recent first). It supports optional pagination and timeframe filtering.

    Query Parameters:
        page (int, optional): The page number for pagination.
        per_page (int, optional): The number of items per page for pagination.
        timeframe (str, optional): Filter by timeframe ('1D', '1W', '1M')

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (list): List of top story articles, each as a dictionary
            - count (int): Number of articles returned
            - total (int): Total number of top stories (only with pagination)
            - page (int): Current page number (only with pagination)
            - pages (int): Total number of pages (only with pagination)
            - error (str or None): Error message, if any
    """
    try:
        # Check if pagination is requested
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)
        timeframe = request.args.get('timeframe')

        # Validate timeframe if provided
        valid_timeframes = ['1D', '1W', '1M']
        if timeframe and timeframe not in valid_timeframes:
            return jsonify(create_response(
                error=f"Invalid timeframe: {timeframe}. Must be one of: {', '.join(valid_timeframes)}"
            )), HTTPStatus.BAD_REQUEST
        
        # Base query for top stories
        query = Article.query.filter_by(is_top_story=True)
        
        # Add timeframe filter if specified
        if timeframe:
            query = query.join(Article.timeframes).filter(ArticleTimeframe.timeframe == timeframe)
        
        # Order by date
        query = query.order_by(desc(Article.date))
        
        if page is not None and per_page is not None:
            # Use pagination
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            top_stories = pagination.items
            result = [article.as_dict() for article in top_stories]
            
            return jsonify(create_response(
                success=True,
                data=result,
                count=len(result),
                total=pagination.total,
                page=page,
                pages=pagination.pages,
                timeframe=timeframe
            )), HTTPStatus.OK
        else:
            # No pagination, return all top stories
            top_stories = query.all()
            result = [article.as_dict() for article in top_stories]
            
            return jsonify(create_response(
                success=True,
                data=result,
                count=len(result),
                timeframe=timeframe
            )), HTTPStatus.OK

    except ValueError as ve:
        return jsonify(create_response(
            error=f"Invalid input: {str(ve)}"
        )), HTTPStatus.BAD_REQUEST
    
    except Exception as e:
        db.session.rollback()
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
