from app.routes.routes_utils import create_response
from flask import request, Blueprint, jsonify
from sqlalchemy.orm.exc import NoResultFound
from config import db, Article
from http import HTTPStatus
from sqlalchemy import desc


top_stories_bp = Blueprint(
    'top_stories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@top_stories_bp.route('/top-stories', methods=['GET'])
def get_top_stories():
    """
    Retrieve top stories from the article database.

    This endpoint queries the database for articles marked as top stories,
    ordered by date (most recent first), with an optional limit on the number of results.

    Args:
        limit (int, optional): The maximum number of top stories to retrieve.
                               Defaults to 10 if not provided.

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (list): List of top story articles, each as a dictionary
            - count (int): Number of articles returned
            - error (str or None): Error message, if any
        HTTP Status Code

    Raises:
        400 Bad Request: If the provided limit is not a valid integer
        500 Internal Server Error: If there's an unexpected error during execution
    """
    try:
        # Get the limit parameter from the query string, default to 10 if not provided
        limit = request.args.get('limit', default=10, type=int)
        
        if not isinstance(limit, int) or limit <= 0:
            return jsonify(create_response(error="Invalid limit parameter")), HTTPStatus.BAD_REQUEST
        
        # Query the database for top stories
        top_stories = Article.query.filter_by(is_top_story=True)\
                                   .order_by(desc(Article.date))\
                                   .limit(limit)\
                                   .all()
        
        # Convert the results to a list of dictionaries
        result = [article.as_dict() for article in top_stories]
        
        return jsonify(create_response(
            success=True,
            data=result,
            count=len(result)
        )), HTTPStatus.OK

    except ValueError as ve:
        db.session.rollback()
        return jsonify(create_response(error=f"Invalid input: {str(ve)}")), HTTPStatus.BAD_REQUEST
    
    except Exception as e:
        db.session.rollback()
        return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), HTTPStatus.INTERNAL_SERVER_ERROR


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


@top_stories_bp.route('/top-story/<int:article_id>', methods=['DELETE'])
def remove_top_story(article_id):
    """
    Remove an article from top stories by setting its is_top_story flag to False.

    This endpoint updates a specific article in the database, changing its is_top_story
    status to False based on the given ID.

    Args:
        article_id (int): The ID of the article to remove from top stories.

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (dict): Contains the ID of the updated article
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
        
        # Update the is_top_story flag
        article.is_top_story = False
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