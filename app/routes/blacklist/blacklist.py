from io import StringIO
from flask import Blueprint, request, jsonify, send_file
from app.routes.routes_utils import create_response, handle_db_session
from config import Blacklist, Bot, db
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

blacklist_bp = Blueprint(
    'blacklist_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@blacklist_bp.route('/get_blacklist', methods=['GET'])
@handle_db_session
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
    bot_id = request.args.get('bot_id')
    if bot_id is None:
        return create_response(error='Bot ID missing in request data'), 400

    try:
        blacklist_data = Blacklist.query.filter_by(bot_id=bot_id).all()
        if not blacklist_data:
            return create_response(error=f'Blacklist with ID: {str(bot_id)} not found'), 404
    
        response = create_response(success=True, data=[blacklist.as_dict() for blacklist in blacklist_data])
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        return create_response(error=f"Database error: {str(e)}"), 500
    except Exception as e:
        return create_response(error=f"Internal server error: {str(e)}"), 500

@blacklist_bp.route('/bots/<int:bot_id>/download/blacklist', methods=['GET'])
@handle_db_session
def download_blacklist(bot_id):
    """
    Download the blacklist of a specific bot in TXT format.

    Args:
        bot_id (int): The ID of the bot to retrieve the blacklist for.

    Response:
        200: Successfully downloaded the blacklist.
        400: Invalid bot ID or bot not found.
        500: Internal server error.
    """
    try:
        bot = Bot.query.get(bot_id)
        if not bot:
            response = create_response(error='Bot not found')
            return jsonify(response), 404
        
        blacklist_data = Blacklist.query.filter_by(bot_id=bot_id).all()
        if not blacklist_data:
            response = create_response(error='No blacklist entries found')
            return jsonify(response), 404
        
        # Create TXT file content
        output = StringIO()
        output.write(f"Blacklist for bot {bot.name}\n\n")
        for entry in blacklist_data:
            output.write(f"{entry.name}\n")
        
        output.seek(0)
        filename = f"{bot.name.replace(' ', '_')}_blacklist_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
        
        return send_file(
            StringIO(output.getvalue()), 
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        response = create_response(error=f"Internal server error: {str(e)}")
        return jsonify(response), 500

@blacklist_bp.route('/add_to_blacklist', methods=['POST'])
@handle_db_session
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
    
    data = request.json
    bot_id = data.get('bot_id')
    blacklist_entries = data.get('blacklist')

    if not bot_id or not blacklist_entries:
        return create_response(error='Bot ID or blacklist entry missing in request data'), 400

    entries = [entry.strip() for entry in blacklist_entries.split(',')]

    try:
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
        response = create_response(success=True, data=[entry.as_dict() for entry in new_entries], message='Entries added to blacklist successfully')
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f"Database error: {str(e)}"), 500
    except Exception as e:
        return create_response(error=f"Internal server error: {str(e)}"), 500


@blacklist_bp.route('/delete_from_blacklist', methods=['DELETE'])
@handle_db_session
def delete_from_blacklist():
    """
    Delete an entry from the blacklist by ID.
    
    Args:
        blacklist_id (int): The ID of the blacklist entry to delete.
    
    Returns:
        JSON response with the result of deleting the entry from the blacklist or an error message.
    """
    blacklist_id = request.args.get('blacklist_id')

    if not blacklist_id:
        return create_response(error='Blacklist ID missing in request data'), 400

    try:
        entry = Blacklist.query.get(blacklist_id)
        if not entry:
            return create_response(error='Entry not found'), 404

        db.session.delete(entry)
        db.session.commit()

        response = create_response(success=True, message='Entry deleted from blacklist successfully')
        return jsonify(response), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return create_response(error=f"Database error: {str(e)}"), 500
    except Exception as e:
        return create_response(error=f"Internal server error: {str(e)}"), 500
