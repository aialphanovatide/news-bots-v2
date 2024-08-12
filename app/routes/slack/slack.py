from datetime import datetime
from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Article, db
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from app.services.slack.actions import send_WARNING_message_to_slack_channel
import json
import re

NEWS_BOT_ERRORS_SLACK_CHANNEL = "C070SM07NGL"

slack_action_bp = Blueprint(
    'slack_action_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

    
@slack_action_bp.route("/slack/events", methods=["POST"])
@measure_execution_time
@handle_db_session
def slack_events():
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
            send_WARNING_message_to_slack_channel(
                channel_id=NEWS_BOT_ERRORS_SLACK_CHANNEL,
                title_message='Error in Slack Action',
                sub_title='Reason',
                message=response.get('error', 'Unknown error occurred')
            )
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
        print(url)
        url = clean_url(url)
        if not url:
            return {'success': False, 'error': 'No valid URL found in the slack message'}

        # Find the article in the database using the extracted URL
        existing_article = Article.query.filter_by(url=url).first()
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
        if block.get('type') == 'section' and 'fields' in block:
            for field in block['fields']:
                url = extract_url_from_text(field.get('text', ''))
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
    url_pattern = r'https?://[^\s"]+'  
    match = re.search(url_pattern, text)
    if match:
        return match.group(0)
    return None


