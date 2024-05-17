from flask import Blueprint, jsonify, request
from config import Article, db
from datetime import datetime
import json
import re

slack_action_bp = Blueprint(
    'slack_action_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

def handle_block_actions(data):
    actions = data.get('actions', [])
    response = {'success': False, 'error': None, 'message': None}

    if not actions:
        response['error'] = 'No actions found'
        return response
    
    article_data = {}

    # Process actions triggered by buttons or text fields
    for action in actions:
        action_id = action.get('action_id')
        value = action.get('value')
        if action_id and value:
            article_data['action_id'] = action_id
            article_data['value'] = value

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
        response['error'] = 'No data found'
        return response
    
  
    # Assuming Article is your SQLAlchemy model
    existing_article = Article.query.filter_by(url=article_data['article_link']).first()
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
            db.session.commit()
            response['success'] = True
            response['message'] = f'Article updated as {article_data["value"]} successfully'
        else:
            # Handle the case when action ID doesn't match any expected value
            response['error'] = f'Unknown action ID: {article_data["action_id"]}'
    else:
        response['error'] = 'Article not found in the database'

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
            if 'error' in response:
                # SEND MESSAGE TO SLACK
                return jsonify({'error': response['error']}), 400
            return jsonify({'status': 'success'}), 200  
        else:
            return jsonify({'error': 'Unknown event type'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    



    #     data = request.get_data().decode('utf-8')  # Decode the bytes to a string
    #     payload = unquote(data.split('payload=')[1])  # Extract and decode the payload

    #     payload_dict = json.loads(payload)
    #     value = payload_dict['actions'][0]['value']
        
    #     # Decode the URL-encoded value and replace '+' with spaces
    #     url = unquote(value).replace('+', ' ').strip()
    #     url = url.split('linkToArticle:')[1]
        
    #     article = session.query(Article).filter(func.trim(Article.url) == url.strip()).first()
    #     if not article:
    #         print('Article not found')
    #         send_INFO_message_to_slack_channel(channel_id="C06FTS38JRX",
    #                                            title_message="Error saving article in top story section",
    #                                            sub_title="Response",
    #                                            message=f"Article with link: {url} - not found")
    #         return 'Article not found', 404
        
    #     if article:
    #         is_top_story_article = session.query(TopStory).filter(TopStory.top_story_id == article.article_id).first()

    #         if is_top_story_article:
    #             send_INFO_message_to_slack_channel(channel_id="C06FTS38JRX",
    #                                            title_message="Error saving article in top story section",
    #                                            sub_title="Response",
    #                                            message=f"Article with link: {url} already exist.")
    #             return 'Article already exist', 409 

    #         if not is_top_story_article:
    #             article_image = session.query(ArticleImage).filter(ArticleImage.article_id == article.article_id).first()
    #             new_topstory = TopStory(coin_bot_id=article.coin_bot_id,
    #                                     summary=article.summary,
    #                                     story_date=article.date)
                                
    #             session.add(new_topstory)
    #             session.commit()
                
    #             image = article_image.image if article_image else "No image"
    #             new_topstory_image = TopStoryImage(image=image,
    #                                                 top_story_id=new_topstory.top_story_id)
    #             session.add(new_topstory_image)
    #             session.commit()

    #             return 'Message received', 200

    # except JSONDecodeError as e:
    #     print(f"Error decoding JSON: {e}")
    #     send_INFO_message_to_slack_channel(channel_id="C06FTS38JRX",
    #                                            title_message="Error saving article in top story section",
    #                                            sub_title="Response",
    #                                            message=f"Error decoding JSON: {e}")
    #     return 'Bad Request: Invalid JSON', 400

    # except KeyError as e:
    #     print(f"Error accessing key in JSON: {e}")
    #     send_INFO_message_to_slack_channel(channel_id="C06FTS38JRX",
    #                                            title_message="Error saving article in top story section",
    #                                            sub_title="Response",
    #                                            message=f"Error accessing key in JSON: {e}")
    #     return 'Bad Request: Missing key in JSON', 400

    # except Exception as e:
    #     print(f"Unexpected error: {e}")
    #     send_INFO_message_to_slack_channel(channel_id="C06FTS38JRX",
    #                                            title_message="Error saving article in top story section",
    #                                            sub_title="Response",
    #                                            message=f"Unexpected error: {e}")
    #     return 'Internal Server Error', 500