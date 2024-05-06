from flask import Blueprint, jsonify, request
from config import Blacklist, db

blacklist_bp = Blueprint(
    'blacklist_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Ruta para obtener todas las filas filtradas por bot_id
@blacklist_bp.route('/get_blacklist_by_bot', methods=['POST'])
def get_blacklist_by_bot():
    try:
        data = request.json
        bot_id = data.get('bot_id')

        if bot_id is None:
            return jsonify({'error': 'Bot ID missing in request data'}), 400

        blacklist = Blacklist.query.filter_by(bot_id=bot_id).all()

        blacklist_data = []
        for entry in blacklist:
            blacklist_data.append({
                'id': entry.id,
                'name': entry.name,
                'bot_id': entry.bot_id,
                'created_at': entry.created_at,
                'updated_at': entry.updated_at
            })

        return jsonify(blacklist_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para agregar una entrada en la blacklist por bot_id
@blacklist_bp.route('/add_to_blacklist', methods=['POST'])
def add_to_blacklist():
    try:
        data = request.json
        name = data.get('name')
        bot_id = data.get('bot_id')

        if name is None or bot_id is None:
            return jsonify({'error': 'Name or Bot ID missing in request data'}), 400

        new_entry = Blacklist(name=name, bot_id=bot_id)
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({'message': 'Entry added to blacklist successfully', 'blacklist_id': new_entry.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
# Ruta para eliminar una entrada de la blacklist por ID 
@blacklist_bp.route('/delete_from_blacklist', methods=['DELETE'])
def delete_from_blacklist():
    try:
        data = request.json
        blacklist_id = data.get('blacklist_id')

        if blacklist_id is None:
            return jsonify({'error': 'Blacklist ID missing in request data'}), 400

        entry = Blacklist.query.get(blacklist_id)
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return jsonify({'message': 'Entry deleted from blacklist successfully'}), 200
        else:
            return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
