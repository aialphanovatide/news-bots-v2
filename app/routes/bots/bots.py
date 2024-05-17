import re
import asyncio
from datetime import datetime
from app.utils.index import fetch_news_links
from flask import Blueprint, jsonify, request
from config import Blacklist, Bot, Keyword, Site, db

bots_bp = Blueprint(
    'bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get all available bots
@bots_bp.route('/bots', methods=['GET'])
def get_bots():
    try:
        bots = Bot.query.all()
        bot_data = [
            {
                'id': bot.id,
                'name': bot.name,
                'category_id': bot.category_id,
            }
        for bot in bots]

        return jsonify({'bots': bot_data}), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    
# Create and schedule a new news Bot
@bots_bp.route('/create_bot', methods=['POST'])
async def create_bot():
    try:
        data = request.json

        # Required inputs
        required_fields = ['name', 'category_id', 'url', 'keywords', 'blacklist']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field in request data: {field}'}), 400

        # verify existing bot
        existing_bot = Bot.query.filter_by(name=data['name']).first()
        if existing_bot:
            return jsonify({'error': f"A bot with the name '{data['name']}' already exists"}), 400

        # Create new bot
        new_bot = Bot(name=data['name'], category_id=data['category_id'])
        db.session.add(new_bot)
        db.session.commit()

        # Create new Site
        url = data['url']
        site_name_match = re.search(r"https://www\.([^.]+)\.com", url)
        if site_name_match:
            site_name = site_name_match.group(1)
        else:
            site_name = 'Google News'
        new_site = Site(name=site_name, url=url, bot_id=new_bot.id)
        db.session.add(new_site)
        db.session.commit()

        # Add keywords to the bot
        keywords = [keyword.strip() for keyword in data['keywords'].split(',')]
        current_time = datetime.now()

        for keyword in keywords:
            new_keyword = Keyword(
                name=keyword,
                bot_id=new_bot.id,
                created_at=current_time,
                updated_at=current_time
            )
            db.session.add(new_keyword)
        
        # Add words to the bot Blacklist 
        blacklist = [keyword.strip() for keyword in data['blacklist'].split(',')]
        for word in blacklist:
            new_blacklist_entry = Blacklist(
                name=word,
                bot_id=new_bot.id,
                created_at=current_time,
                updated_at=current_time
            )
            db.session.add(new_blacklist_entry)
        
        db.session.commit()
        
        # run fetch news link function after create a bot 
        await fetch_news_links( 
            url=data['url'],  
            blacklist=data['blacklist'].split(','), 
            category_id=data['category_id'],
            bot_id=new_bot.id,
            bot_name=new_bot.name
        )

        return jsonify({'message': 'Bot created and automated successfully', 'bot_id': new_bot.id, 'news_links': data['url']}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

  
# Delete a single Bot by ID
@bots_bp.route('/delete_bots', methods=['DELETE'])
def delete_bot():
    try:
        data = request.get_json()

        if not data or 'id' not in data:
            return jsonify({'error': 'Bot ID is missing from request data'}), 400

        bot_id = data['id']
        bot = Bot.query.get(bot_id)

        if not bot:
            return jsonify({'error': 'Bot not found'}), 404

        db.session.delete(bot)
        db.session.commit()

        return jsonify({'message': f'Bot with ID {bot_id} deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    
    