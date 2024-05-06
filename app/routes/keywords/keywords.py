from flask import Blueprint, jsonify, request
from config import Keyword, db

keyword_bp = Blueprint(
    'keyword_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Ruta para obtener todas las filas filtradas por bot_id
@keyword_bp.route('/get_keywords_by_bot', methods=['POST'])
def get_keywords_by_bot():
    try:
        data = request.json
        bot_id = data.get('bot_id')

        if bot_id is None:
            return jsonify({'error': 'Bot ID missing in request data'}), 400

        keywords = Keyword.query.filter_by(bot_id=bot_id).all()

        keyword_data = []
        for entry in keywords:
            keyword_data.append({
                'id': entry.id,
                'name': entry.name,
                'bot_id': entry.bot_id,
                'created_at': entry.created_at,
                'updated_at': entry.updated_at
            })

        return jsonify({'message': keyword_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para agregar una entrada en la blacklist por bot_id
@keyword_bp.route('/add_keyword_to_bot', methods=['POST'])
def add_keyword_to_bot():
    try:
        data = request.json
        name = data.get('name')
        bot_id = data.get('bot_id')

        if name is None or bot_id is None:
            return jsonify({'error': 'Name or Bot ID missing in request data'}), 400

        new_keyword = Keyword(name=name, bot_id=bot_id)
        db.session.add(new_keyword)
        db.session.commit()

        return jsonify({'message': 'Keyword added to bot successfully', 'keyword_id': new_keyword.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para eliminar una entrada de la blacklist por ID
@keyword_bp.route('/delete_keyword_from_bot', methods=['DELETE'])
def delete_keyword_from_bot():
    try:
        data = request.json
        keyword_id = data.get('keyword_id')

        if keyword_id is None:
            return jsonify({'error': 'Keyword ID missing in request data'}), 400

        keyword = Keyword.query.get(keyword_id)
        if keyword:
            db.session.delete(keyword)
            db.session.commit()
            return jsonify({'message': 'Keyword deleted from bot successfully'}), 200
        else:
            return jsonify({'error': 'Keyword not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
