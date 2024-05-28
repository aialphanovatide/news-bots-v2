from flask import Blueprint, jsonify, request
from config import Article, db
from datetime import datetime
from app.services.slack.actions import send_WARNING_message_to_slack_channel
import json
import re

slack_action_bp = Blueprint(
    'slack_action_bp', __name__,
    template_folder='templates',
    static_folder='static'
)



def extract_url_from_text(text):
    url_pattern = r'<(https?://[^\s]+)>'
    match = re.search(url_pattern, text)
    if match:
        return match.group(1)
    return None

# Handles the DB modification of the article
def handle_block_actions(data):
    actions = data.get('actions', [])

    response = {'success': False, 'error': None, 'message': None}

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

<<<<<<< HEAD
    # Extract additional comments
    state = data.get('state', {}).get('values', {})
    for block_id, block in state.items():
        for action_id, action in block.items():
            if action_id == 'additional_comments':
                article_data['additional_comments'] = action.get('value', '')

    # Find the article link to use for querying the DB
    message = data.get('message', {})
    attachments = message.get('attachments', [])
    if attachments:
        for attachment in attachments:
            title_link = attachment.get('title_link')
            title = attachment.get('title')
            if title_link and title:
                article_data['article_link'] = title_link
                article_data['title'] = title

    if not article_data.keys():
        response['error'] = 'No data found in the slack message for querying the database'
=======
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
>>>>>>> d5bfca3f647fc2a139f0cb8bd36cd18ac12aea35
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
            existing_article.is_article_efficent = f"{article_data['action_id']} - {article_data['value']}"
            existing_article.additional_comments = article_data.get('additional_comments', '')
            db.session.commit()
            response['success'] = True
            response['message'] = f'Article updated with: {article_data["value"]} AS feedback and additional comments'
        else:
            # Handle the case when action ID doesn't match any expected value
            response['error'] = f'Unknown action ID: {article_data["action_id"]} while updating the article'
    else:
        response['error'] = f'Article not found in the database'

    return response

# RESERVED ROUTE - DO NOT USE
# This route receives all relevant articles that needs to go to the Top Stories as well as feedback
@slack_action_bp.route("/slack/events", methods=["POST"])
def slack_events():
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
            print('response: ', response)
            if 'error' in response and response['error'] is not None:
                # SEND MESSAGE TO SLACK
                send_WARNING_message_to_slack_channel(channel_id='C070SM07NGL',
                                                      title_message='Error while updating news',
                                                      sub_title='Reason',
                                                      message=response['error']
                                                      )
                return jsonify({'error': response['error']}), 400
            return jsonify({'status': 'success'}), 200  
        else:
            return jsonify({'error': 'Unknown event type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
