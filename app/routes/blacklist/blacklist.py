from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from config import db, Blacklist, Bot
from datetime import datetime

blacklist_bp = Blueprint('blacklist_bp', __name__)

@blacklist_bp.route('/blacklist', methods=['POST'])
@handle_db_session
def add_to_blacklist():
    """
    Add entries to the blacklist for multiple bots.

    Request Body:
        JSON data with 'entries' (list of str) and 'bot_ids' (list of int).

    Response:
        201: Successfully added entries to the blacklist.
        400: Invalid request data.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        entries = data.get('entries', [])
        bot_ids = data.get('bot_ids', [])

        if not entries or not bot_ids or not isinstance(entries, list) or not isinstance(bot_ids, list):
            return jsonify(create_response(error='Invalid request data. Provide lists of entries and bot_ids.')), 400

        # Validate bot_ids
        valid_bots = Bot.query.filter(Bot.id.in_(bot_ids)).all()
        valid_bot_ids = {bot.id for bot in valid_bots}
        if len(valid_bot_ids) != len(bot_ids):
            invalid_ids = set(bot_ids) - valid_bot_ids
            return jsonify(create_response(error=f'Invalid bot IDs: {invalid_ids}')), 400

        # Get existing blacklist entries for the specified bots
        existing_entries = Blacklist.query.filter(Blacklist.bot_id.in_(bot_ids)).all()
        existing_entry_map = {(entry.name.lower(), entry.bot_id) for entry in existing_entries}

        new_entries = []
        current_time = datetime.utcnow()

        # Prepare new blacklist entries
        for bot_id in valid_bot_ids:
            for entry in entries:
                entry = entry.strip().lower()
                if (entry, bot_id) not in existing_entry_map:
                    new_entries.append(Blacklist(
                        name=entry,
                        bot_id=bot_id,
                        created_at=current_time,
                        updated_at=current_time
                    ))

        # Bulk insert new entries
        if new_entries:
            db.session.bulk_save_objects(new_entries)
            db.session.commit()

        response = create_response(
            success=True,
            message=f'{len(new_entries)} entries added to blacklist across {len(valid_bot_ids)} bots.',
            data={'added_count': len(new_entries), 'affected_bots': len(valid_bot_ids)}
        )
        return jsonify(response), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@blacklist_bp.route('/blacklist', methods=['DELETE'])
@handle_db_session
def delete_from_blacklist():
    """
    Delete entries from the blacklist for multiple bots.

    Request Body:
        JSON data with 'entry_ids' (list of int) and/or 'entries' (list of str) and 'bot_ids' (list of int).

    Response:
        200: Entries deleted from blacklist successfully.
        400: Invalid request data.
        404: No matching blacklist entries found.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        entry_ids = data.get('entry_ids', [])
        entries = data.get('entries', [])
        bot_ids = data.get('bot_ids', [])

        if not bot_ids or not isinstance(bot_ids, list):
            return jsonify(create_response(error='Invalid request data. Provide bot_ids as a list.')), 400

        if not entry_ids and not entries:
            return jsonify(create_response(error='Invalid request data. Provide either entry_ids or entries.')), 400

        query = Blacklist.query.filter(Blacklist.bot_id.in_(bot_ids))

        conditions = []
        if entry_ids:
            conditions.append(Blacklist.id.in_(entry_ids))
        if entries:
            conditions.append(Blacklist.name.in_([entry.strip().lower() for entry in entries]))

        query = query.filter(or_(*conditions))

        entries_to_delete = query.all()

        if not entries_to_delete:
            return jsonify(create_response(error='No matching blacklist entries found')), 404

        for entry in entries_to_delete:
            db.session.delete(entry)

        db.session.commit()

        response = create_response(
            success=True,
            message=f'{len(entries_to_delete)} entries deleted from blacklist across {len(set(entry.bot_id for entry in entries_to_delete))} bots.',
            data={
                'deleted_count': len(entries_to_delete),
                'affected_bots': len(set(entry.bot_id for entry in entries_to_delete))
            }
        )
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500

@blacklist_bp.route('/blacklist/search', methods=['POST'])
@handle_db_session
def search_blacklist():
    """
    Search for blacklist entries across specified bots for multiple queries.

    Request Body:
        JSON data with 'queries' (list of str) and 'bot_ids' (list of int).

    Response:
        200: Successfully retrieved relevant blacklist entries.
        400: Invalid request data.
        404: No related entries found.
        500: Server error.
    """
    try:
        data = request.json
        queries = data.get('queries', [])
        bot_ids = data.get('bot_ids', [])

        if not queries or not bot_ids or not isinstance(queries, list) or not isinstance(bot_ids, list):
            return jsonify(create_response(error='Invalid request data. Provide lists of queries and bot_ids.')), 400

        # Fetch bot names
        bots = Bot.query.filter(Bot.id.in_(bot_ids)).all()
        bot_id_to_name = {bot.id: bot.name for bot in bots}

        # Conduct search through the blacklist table
        blacklist_results = (Blacklist.query
                             .filter(Blacklist.bot_id.in_(bot_ids))
                             .filter(or_(*[Blacklist.name.ilike(f'%{query.lower()}%') for query in queries]))
                             .all())

        if not blacklist_results:
            return jsonify(create_response(error='No related entries found')), 404

        # Prepare results
        blacklist = [{**bl.as_dict(), 'bot_name': bot_id_to_name.get(bl.bot_id, 'Unknown')} for bl in blacklist_results]

        return jsonify(create_response(success=True, data={'blacklist': blacklist})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500