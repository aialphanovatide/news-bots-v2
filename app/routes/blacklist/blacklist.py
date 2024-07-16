from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Blacklist, db
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

blacklist_bp = Blueprint(
    'blacklist_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@blacklist_bp.route('/get_blacklist', methods=['GET'])
@measure_execution_time
def get_blacklist_by_bot():
    """
    Get blacklist of a specific bot.

    Args:
        bot_id (int): The ID of the bot to retrieve the blacklist for.

    Response:
        200: Successfully retrieved the blacklist.
        400: Bot ID missing in request data.
        404: Blacklist not found for the specified bot ID.
        500: Internal server error.

    """
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')

        if bot_id is None:
            response['error'] = 'Bot ID missing in request data'
            return jsonify(response), 400

        blacklist_data = Blacklist.query.filter_by(bot_id=bot_id).all()
        if not blacklist_data:
            response['error'] = f'Blacklist with ID: {str(bot_id)} not found'
            return jsonify(response), 404

        response['data'] = [blacklist.as_dict() for blacklist in blacklist_data]
        response['success'] = True
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


@blacklist_bp.route('/add_to_blacklist', methods=['POST'])
def add_to_blacklist():
    """
    Add an entry to the blacklist for a specific bot.

    Args:
        bot_id (int): The ID of the bot to add entries to the blacklist for.
        blacklist (str): A comma-separated list of entries to add to the blacklist.

    Response:
        200: Successfully added entries to the blacklist.
        400: Bot ID or blacklist entry missing in request data.
        500: Internal server error.
    """

    response = {'data': [], 'error': None, 'success': False}
    try:
        data = request.json
        blacklist_entries = data.get('blacklist')
        bot_id = data.get('bot_id')

        if not bot_id or not blacklist_entries:
            response['error'] = 'Bot ID or blacklist entry missing in request data'
            return jsonify(response), 400

        entries = [entry.strip() for entry in blacklist_entries.split(',')]

        for entry in entries:
            existing_blacklist = Blacklist.query.filter_by(bot_id=bot_id, name=entry.casefold()).first()
            if existing_blacklist:
                continue

            new_entry = Blacklist(
                name=entry,
                bot_id=bot_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(new_entry)

        db.session.commit()

        new_entries = Blacklist.query.filter(Blacklist.name.in_(entries), Blacklist.bot_id == bot_id).all()
        response['data'] = [entry.as_dict() for entry in new_entries]
        response['success'] = True
        response['message'] = 'Entries added to blacklist successfully'
        return jsonify(response), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500


@blacklist_bp.route('/delete_from_blacklist', methods=['DELETE'])
def delete_from_blacklist():
    """
    Delete an entry from the blacklist by ID.
    Args:
        blacklist_id (int): The ID of the blacklist entry to delete.
    Response:
        200: Successfully deleted the entry from the blacklist.
        400: Blacklist ID missing in request data.
        404: Entry not found.
        500: Internal server error.
    """
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
            response['message'] = 'Entry deleted from blacklist successfully'
            response['success'] = True
            return jsonify(response), 200
        else:
            response['error'] = 'Entry not found'
            return jsonify(response), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        response['error'] = f'Database error: {str(e)}'
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500
