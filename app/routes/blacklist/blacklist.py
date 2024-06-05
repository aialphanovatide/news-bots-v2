from flask import Blueprint, jsonify, request
from config import Blacklist, db
from datetime import datetime

blacklist_bp = Blueprint(
    'blacklist_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get blacklist of a bot
@blacklist_bp.route('/get_blacklist', methods=['GET'])
def get_blacklist_by_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Get bot ID from request arguments
        bot_id = request.args.get('bot_id')

        if bot_id is None:
            response['error'] = 'Bot ID missing in request data'
            return jsonify(response), 400

        # Query blacklist data for the bot
        blacklist_data = Blacklist.query.filter_by(bot_id=bot_id).all()
        if not blacklist_data:
            response['error'] = f'blacklist with ID: {str(bot_id)} not found'
            return jsonify(response), 404

        # Prepare the response with blacklist data
        blacklist_data = [blacklist.as_dict() for blacklist in blacklist_data]
        response['data'] = blacklist_data
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500
    

# Add an entry to the blacklist by bot_id
@blacklist_bp.route('/add_to_blacklist', methods=['POST'])
def add_to_blacklist():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.json
        blacklist_entry = data.get('blacklist')
        bot_id = data.get('bot_id')
        print()

        if not bot_id or not blacklist_entry:
            response['error'] = 'Bot ID or Blacklist entry missing in request data'
            return jsonify(response), 400

        # Find the blacklist associated with the provided bot ID
        existing_blacklist = Blacklist.query.filter_by(bot_id=bot_id, name=blacklist_entry.casefold()).first()
        if existing_blacklist:
            response['error'] = f'Blacklist entry "{blacklist_entry}" already exists for bot with ID {bot_id}'
            return jsonify(response), 400

        # Add a new entry to the blacklist
        new_entry = Blacklist(name=blacklist_entry, 
                              bot_id=bot_id,
                              created_at=datetime.now(),
                              updated_at=datetime.now()
                              )
        db.session.add(new_entry)
        db.session.commit()

        # Prepare the success response with the data of the new blacklist entry
        response['data'] = new_entry.as_dict()
        response['success'] = True
        response['message'] = 'Entry added to blacklist successfully'
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


    
    
# Delete an entry from the blacklist by ID
@blacklist_bp.route('/delete_from_blacklist', methods=['DELETE'])
def delete_from_blacklist():
    response = {'message': None, 'error': None, 'success': False}
    try:
        blacklist_id = request.args.get('blacklist_id')

        if blacklist_id is None or not blacklist_id:
            response['error'] = 'Blacklist ID missing in request data'
            return jsonify(response), 400

        entry = Blacklist.query.get(blacklist_id)
        if entry:
            db.session.delete(entry)
            db.session.commit()
            response['message'] = f'Entry deleted from blacklist successfully'
            response['success'] = True
            return jsonify(response), 200
        else:
            response['error'] = 'Entry not found'
            return jsonify(response), 404
    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

