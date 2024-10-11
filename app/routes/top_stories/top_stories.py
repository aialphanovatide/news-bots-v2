from app.routes.routes_utils import create_response
from flask import request, Blueprint, jsonify
from sqlalchemy.orm.exc import NoResultFound
from config import db, Article
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
    Set an article as a top story.

    This endpoint takes an article ID as a URL parameter and sets its is_top_story field to True.

    URL Parameters:
        article_id (int): The ID of the article to be set as a top story

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - message (str): A message describing the result of the operation
            - data (dict): The updated article information
            - error (str or None): Error message, if any
        HTTP Status Code

    Raises:
        404 Not Found: If the article with the given ID doesn't exist
        500 Internal Server Error: If there's an unexpected error during execution
    """
    try:
        article = Article.query.get(article_id)

        if not article:
            return jsonify(create_response(error=f"Article with ID {article_id} not found")), HTTPStatus.NOT_FOUND

        article.is_top_story = True
        article.updated_at = datetime.now()
        db.session.commit()

        return jsonify(create_response(
            success=True,
            message=f"Article {article_id} has been set as a top story",
            data=article.as_dict()
        )), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        return jsonify(create_response(error=f"An unexpected error occurred: {str(e)}")), HTTPStatus.INTERNAL_SERVER_ERROR


@top_stories_bp.route('/top-stories', methods=['GET'])
def get_top_stories():
    """
    Retrieve top stories from the article database with optional pagination.

    This endpoint queries the database for articles marked as top stories,
    ordered by date (most recent first). It supports optional pagination.

    Query Parameters:
        page (int, optional): The page number for pagination.
        per_page (int, optional): The number of items per page for pagination.

    Returns:
        JSON: A JSON object containing:
            - success (bool): Indicates if the operation was successful
            - data (list): List of top story articles, each as a dictionary
            - count (int): Number of articles returned
            - total (int): Total number of top stories (only with pagination)
            - page (int): Current page number (only with pagination)
            - pages (int): Total number of pages (only with pagination)
            - error (str or None): Error message, if any
        HTTP Status Code

    Raises:
        400 Bad Request: If the provided parameters are not valid
        500 Internal Server Error: If there's an unexpected error during execution
    """
    try:
        # Check if pagination is requested
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)
        
        # Query for top stories
        query = Article.query.filter_by(is_top_story=True).order_by(desc(Article.date))
        
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
                pages=pagination.pages
            )), HTTPStatus.OK
        else:
            # No pagination, return all top stories
            top_stories = query.all()
            result = [article.as_dict() for article in top_stories]
            
            return jsonify(create_response(
                success=True,
                data=result,
                count=len(result)
            )), HTTPStatus.OK

    except ValueError as ve:
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
    




# RESERVED ENDPOINT - DO NOT DELETE
@top_stories_bp.route("/slack/events", methods=["POST"])
@handle_db_session
def post_top_stories():
    try:
        payload = request.form.get('payload')
        if not payload:
            return jsonify(create_response(success=False, error='Missing payload')), 400

        data = json.loads(payload)
        event_type = data.get('type')

        if event_type != 'block_actions':
            return jsonify(create_response(success=False, error='Unsupported event type')), 400

        response = handle_block_actions(data)

        if not response.get('success'):
            # send_WARNING_message_to_slack_channel(
            #     channel_id=NEWS_BOT_ERRORS_SLACK_CHANNEL,
            #     title_message='Error in Slack Action',
            #     sub_title='Reason',
            #     message=response.get('error', 'Unknown error occurred')
            # )
            return jsonify(create_response(success=False, error=response.get('error'))), 400

        return jsonify(create_response(
            success=True, 
            message=response.get('message', 'Operation successful'),
            data=response.get('data')
        )), 200

    except json.JSONDecodeError:
        return jsonify(create_response(success=False, error='Invalid JSON payload')), 400
    except Exception as e:
        return jsonify(create_response(success=False, error=f'Internal server error: {str(e)}')), 500

def clean_url(url):
    """
    Cleans the URL by removing unwanted characters.

    Args:
        url (str): The URL to clean.

    Returns:
        str: The cleaned URL.
    """
    if url:
        return url.replace('<', '').replace('>', '')
    return url

def handle_block_actions(data):
    """
    Handles block actions received from Slack messages to modify articles in the database.
    
    Args:
        data (dict): JSON data containing Slack message blocks and actions.
    
    Returns:
        dict: Response indicating success or failure with appropriate messages.
    """
    try:
        actions = data.get('actions', [])
        if not actions:
            return {'success': False, 'error': 'No actions found in the slack message'}
        
        article_data = {}

        # Process actions triggered by buttons or text fields
        for action in actions:
            action_id = action.get('action_id')
            value = action.get('value')
            if action_id and value:
                article_data['action_id'] = action_id
                article_data['value'] = value
    
        # Extract the URL from the message blocks
        url = extract_url_from_blocks(data['message']['blocks'])

        url = clean_url(url)


        # Find the article in the database using the extracted URL or Grok title
        existing_article = None

        if url:
            existing_article = Article.query.filter_by(url=url).first()
        if not existing_article:
            value = actions[0]['value']
            grok_title = value.split('link_to_article: Grok AI -')[1].strip()
            pre_grok_fix = 'Grok AI - '
            final_grok_url = f'{pre_grok_fix}{grok_title}'
            existing_article = Article.query.filter_by(url=final_grok_url).first()

        if not existing_article:
            return {'success': False, 'error': 'Article not found in the database'}

        # Update the article based on the action
        if article_data['action_id'] == 'add_to_top_story':
            existing_article.is_top_story = True
            message = 'Article added to top story successfully'
        elif article_data['action_id'] in ['green', 'red', 'yellow']:
            existing_article.is_article_efficent = f"{article_data['action_id']} - {article_data['value']}"
            message = f'Article updated with: {article_data["value"]} as feedback and additional comments'
        else:
            return {'success': False, 'error': f'Unknown action ID: {article_data["action_id"]} while updating the article'}

        existing_article.updated_at = datetime.now()
        db.session.commit()

        return {'success': True, 'message': message}

    except SQLAlchemyError as e:
        db.session.rollback()
        return {'success': False, 'error': f'Database error: {str(e)}'}

    except Exception as e:
        return {'success': False, 'error': f'Internal server error: {str(e)}'}
    
def extract_url_from_blocks(blocks):
    """
    Extracts URL from message blocks.

    Args:
        blocks (list): List of message blocks.

    Returns:
        str or None: Extracted URL or None if not found.
    """
    for block in blocks:
        if block.get('type') == 'section':
            if 'fields' in block:
                for field in block['fields']:
                    url = extract_url_from_text(field.get('text', ''))
                    if url:
                        print(f"URL extracted: {url}") 
                        return url
            if 'text' in block:
                url = extract_url_from_text(block['text'].get('text', ''))
                if url:
                    return url
    return None

def extract_url_from_text(text):
    """
    Extracts a URL from the given text using a regular expression.

    Args:
        text (str): The text from which to extract the URL.

    Returns:
        str or None: The extracted URL, or None if no URL is found.
    """
    # El patrón para buscar URLs
    url_pattern = r'<(https?://[^\s]+)>'  
    match = re.search(url_pattern, text)
    if match:
        return match.group(1)  # Retornamos solo la URL sin los corchetes
    return None
