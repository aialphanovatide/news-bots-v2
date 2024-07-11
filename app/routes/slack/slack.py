from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Article, db
from datetime import datetime
from app.services.slack.actions import send_WARNING_message_to_slack_channel
import json
import re
from sqlalchemy.exc import SQLAlchemyError

slack_action_bp = Blueprint(
    'slack_action_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

def extract_url_from_text(text):
    """
    Extracts a URL from the given text using a regular expression.
    
    Args:
        text (str): The text from which to extract the URL.
    
    Returns:
        str or None: The extracted URL, or None if no URL is found.
    """
    url_pattern = r'<(https?://[^\s]+)>'
    match = re.search(url_pattern, text)
    if match:
        return match.group(1)
    return None

def handle_block_actions(data):
    """
    Handles block actions received from Slack messages to modify articles in the database.
    
    Args:
        data (dict): JSON data containing Slack message blocks and actions.
    
    Returns:
        dict: Response indicating success or failure with appropriate messages.
    """
    response = {'success': False, 'error': None, 'message': None}

    try:
        actions = data.get('actions', [])

        if not actions:
            response['error'] = 'No actions found in the slack message'
            return response
        
        article_data = {}

        # Process actions triggered by buttons or text fields
        for action in actions:
            action_id = action.get('action_id')
            value = action.get('value')
            if action_id and value:
                article_data['action_id'] = action_id
                article_data['value'] = value

        # Extract the URL from the message blocks
        fields = data['message']['blocks'][2].get('fields', [])
        url = None

        for field in fields:
            if 'text' in field:
                url = extract_url_from_text(field['text'])
                if url:
                    break  # Exit the loop once the URL is found

        if not url:
            response['error'] = 'No valid URL found in the slack message'
            return response

        # Find the article in the database using the extracted URL
        existing_article = Article.query.filter_by(url=url).first()
        if existing_article:
            if article_data['action_id'] == 'add_to_top_story':
                existing_article.is_top_story = True
                existing_article.updated_at = datetime.now()
                db.session.commit()
                response['success'] = True
                response['message'] = 'Article added to top story successfully'
            elif article_data['action_id'] in ['green', 'red', 'yellow']:
                existing_article.updated_at = datetime.now()
                existing_article.is_article_efficient = f"{article_data['action_id']} - {article_data['value']}"
                existing_article.additional_comments = article_data.get('additional_comments', '')
                db.session.commit()
                response['success'] = True
                response['message'] = f'Article updated with: {article_data["value"]} as feedback and additional comments'
            else:
                # Handle the case when action ID doesn't match any expected value
                response['error'] = f'Unknown action ID: {article_data["action_id"]} while updating the article'
        else:
            response['error'] = 'Article not found in the database'

    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'

    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'

    return response

@slack_action_bp.route("/slack/events", methods=["POST"])
@measure_execution_time
def slack_events():
    """
    Endpoint to receive Slack events and handle block actions.
    
    Returns:
        200: Success response.
        400: Error response with details.
        500: Internal server error.
    """
    try:
        payload = request.form.get('payload')

        if not payload:
            return jsonify({'error': 'Missing payload'}), 400

        # Parse the payload as JSON
        data = json.loads(payload)

        # Type of interaction
        event_type = data.get('type')
        if event_type == 'block_actions':
            # Handle block_actions payload
            response = handle_block_actions(data)
            
            if response.get('error'):
                # Send a warning message to Slack channel on error
                send_WARNING_message_to_slack_channel(
                    channel_id='C070SM07NGL',
                    title_message='Error while updating news',
                    sub_title='Reason',
                    message=response['error']
                )
                return jsonify({'error': response['error']}), 400
            
            return jsonify({'status': 'success', 'message': response.get('message', 'Operation successful')}), 200
        
        else:
            return jsonify({'error': 'Unknown event type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
