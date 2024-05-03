from flask import Blueprint, jsonify, request
from config import Bot, db

bots_bp = Blueprint(
    'bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@bots_bp.route('/bots', methods=['GET'])
def get_bots():
    try:
        bots = Bot.query.all()
        bot_data = []
        for bot in bots:
            bot_data.append({
                'id': bot.id,
                'name': bot.name,
                'category_id': bot.category_id,
            })
        return jsonify(bot_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bots_bp.route('/create_coin_bot', methods=['POST'])
def create_bot():
    try:
        data = request.json
        new_bot = Bot(name=data['name'], category_id=data['category_id'])
        db.session.add(new_bot)
        db.session.commit()
        return jsonify({'message': 'Bot created successfully', 'bot_id': new_bot.id}), 200
    except KeyError as e:
        return jsonify({'error': f'Missing key in request data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@bots_bp.route('/delete_bots', methods=['DELETE'])
def delete_bot():
    try:
        data = request.json

        if 'id' not in data:
            return jsonify({'error': 'Bot ID is missing from request data'}), 400

        bot_id = data['id']
        bot = Bot.query.get(bot_id)

        if not bot:
            return jsonify({'error': 'Bot not found'}), 404

        db.session.delete(bot)
        db.session.commit()

        return jsonify({'message': f'Bot with ID {bot_id} deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500