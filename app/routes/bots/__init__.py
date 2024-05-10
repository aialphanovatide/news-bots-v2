import json
from flask import request

@bots_bp.route('/create_coin_bot', methods=['POST'])
def create_bot():
    try:
        data = request.json
        topic = data['bot_name']
        category = data['category_id']
        keywords = request.json 
        blacklist = request.json
        timeframe = request.json
        url = request.json 

        # if topic already exist throw error, if url exist throu error


        new_bot = Bot(name=topic, category_id=category)
        
        db.session.add(new_bot)
        db.session.commit()
        # agregar a keywords a table
        # agregar blacklist a su table
        # agregar url a site

        

        scheduler(fetch_news_links, timaframe=timeframe, id=topic, date: date.now(), arg=[argumentos])


        return jsonify({'message': 'Bot created successfully', 'bot_id': new_bot.id}), 200
    except KeyError as e:
        return jsonify({'error': f'Missing key in request data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bots_bp.route('/create/tebots', methods=['GET'])
def get_bots():
    try:
        topic = request
        keywords = request
        blacklist = request.json
        timeframe = request.json
        url = request.json

        save_to_
        
        results = fetch_news_links(topic)
        bots = Bot.query.all()
        bot_data = []
        for bot in bots:
            bot_data.append({
                'id': bot.id,
                'name': bot.name,
                'category_id': bot.category_id,
            })
        return jsonify({'message': bot_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500