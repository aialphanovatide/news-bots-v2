from flask import Blueprint, jsonify, request
from config import Blacklist, Keyword, Bot, db
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis, update_cache_with_redis
from app.services.file_extraction.file_extraction import process_uploaded_file

keyword_bp = Blueprint(
    'keyword_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@keyword_bp.route('/keywords', methods=['POST'])
@handle_db_session
@update_cache_with_redis(related_get_endpoints=['get_bot', 'dynamic_search', 'get_all_bots'])
def create_keywords():
    """
    Add keywords to multiple bots in bulk.
    
    Request Body:
        JSON data with 'keywords' (list of str) and 'bot_ids' (list of int).
    
    Response:
        201: Keywords added to bots successfully.
        400: Invalid request data.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        keywords = data.get('keywords', [])
        bot_ids = data.get('bot_ids', [])

        if not keywords or not bot_ids or not isinstance(keywords, list) or not isinstance(bot_ids, list):
            return jsonify(create_response(error='Invalid request data. Provide lists of keywords and bot_ids.')), 400

        # Validate bot_ids
        valid_bots = Bot.query.filter(Bot.id.in_(bot_ids)).all()
        valid_bot_ids = {bot.id for bot in valid_bots}
        if len(valid_bot_ids) != len(bot_ids):
            invalid_ids = set(bot_ids) - valid_bot_ids
            return jsonify(create_response(error=f'Invalid bot IDs: {invalid_ids}')), 400

        # Get existing keywords for the specified bots
        existing_keywords = Keyword.query.filter(Keyword.bot_id.in_(bot_ids)).all()
        existing_keyword_map = {(kw.name.lower(), kw.bot_id) for kw in existing_keywords}

        new_keywords = []
        current_time = datetime.now()

        # Prepare new keywords
        for bot_id in valid_bot_ids:
            for kw in keywords:
                kw = kw.strip().lower()
                if (kw, bot_id) not in existing_keyword_map:
                    new_keywords.append(Keyword(
                        name=kw,
                        bot_id=bot_id,
                        created_at=current_time,
                        updated_at=current_time
                    ))

        # Bulk insert new keywords
        if new_keywords:
            db.session.bulk_save_objects(new_keywords)
            db.session.commit()

        response = create_response(
            success=True,
            message=f'{len(new_keywords)} keywords added across {len(valid_bot_ids)} bots.',
            data={'added_count': len(new_keywords), 'affected_bots': len(valid_bot_ids)}
        )
        return jsonify(response), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@keyword_bp.route('/keywords', methods=['DELETE'])
@handle_db_session
@update_cache_with_redis(related_get_endpoints=['get_bot', 'dynamic_search', 'get_all_bots'])
def delete_keywords():
    """
    Delete keywords from multiple bots in bulk.
    
    Request Body:
        JSON data with 'keyword_ids' (list of int) or 'keywords' (list of str) and 'bot_ids' (list of int).
    
    Response:
        200: Keywords deleted successfully.
        400: Invalid request data.
        404: No matching keywords found.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        keyword_ids = data.get('keyword_ids', [])
        keywords = data.get('keywords', [])
        bot_ids = data.get('bot_ids', [])

        if not (keyword_ids or keywords) or not bot_ids or \
           not isinstance(keyword_ids, list) or not isinstance(keywords, list) or not isinstance(bot_ids, list):
            return jsonify(create_response(error='Invalid request data. Provide keyword_ids (list) or keywords (list), and bot_ids (list).')), 400

        query = Keyword.query.filter(Keyword.bot_id.in_(bot_ids))

        if keyword_ids:
            query = query.filter(Keyword.id.in_(keyword_ids))
        elif keywords:
            query = query.filter(Keyword.name.in_([kw.strip().lower() for kw in keywords]))

        keywords_to_delete = query.all()

        if not keywords_to_delete:
            return jsonify(create_response(error='No matching keywords found')), 404

        for keyword in keywords_to_delete:
            db.session.delete(keyword)

        db.session.commit()

        response = create_response(
            success=True,
            message=f'{len(keywords_to_delete)} keywords deleted across {len(set(kw.bot_id for kw in keywords_to_delete))} bots.',
            data={
                'deleted_count': len(keywords_to_delete),
                'affected_bots': len(set(kw.bot_id for kw in keywords_to_delete))
            }
        )
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@keyword_bp.route('/keywords/search', methods=['POST'])
@handle_db_session
def dynamic_search():
    """
    Search for related keywords and blacklist words across specified bots for multiple queries.
    
    Request Body:
        JSON data with 'queries' (list of str) and 'bot_ids' (list of int).
    
    Response:
        200: Successfully retrieved relevant words.
        400: Invalid request data.
        404: No related words found.
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

        # Conduct search through the keyword and blacklist tables
        keyword_results = (Keyword.query
                           .filter(Keyword.bot_id.in_(bot_ids))
                           .filter(or_(*[Keyword.name.ilike(f'%{query.lower()}%') for query in queries]))
                           .all())
        
        blacklist_results = (Blacklist.query
                             .filter(Blacklist.bot_id.in_(bot_ids))
                             .filter(or_(*[Blacklist.name.ilike(f'%{query.lower()}%') for query in queries]))
                             .all())

        if not keyword_results and not blacklist_results:
            return jsonify(create_response(error='No related words found')), 404

        # Prepare results
        keywords = [{**kw.as_dict(), 'bot_name': bot_id_to_name.get(kw.bot_id, 'Unknown')} for kw in keyword_results]
        blacklist = [{**bl.as_dict(), 'bot_name': bot_id_to_name.get(bl.bot_id, 'Unknown')} for bl in blacklist_results]

        return jsonify(create_response(success=True, data={'whitelist': keywords, 'blacklist': blacklist})), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500


@keyword_bp.route('/keywords/extract', methods=['POST'])
def extract_keywords_and_blacklist():
    """
    Extract keywords and blacklist from an uploaded Excel file (.xls or .xlsx).

    This endpoint accepts an Excel file upload and extracts data from 'keywords' and 'blacklist' tabs.
    The file must have tabs with names containing 'keywords' or 'blacklist' (case-insensitive).
    Each relevant tab must have a column titled 'keywords' or 'blacklist' respectively.

    Request:
        - file: The Excel file to be processed (multipart/form-data)

    Returns:
        JSON response containing:
        - success: Boolean indicating if the operation was successful
        - data: Extracted keywords and blacklist as comma-separated strings
        - message: Description of the operation result
        - error: Error message if any

    Responses:
        200: File processed successfully
        400: Bad request (no file, unsupported file type, missing required tabs/columns)
        500: Internal server error
    """
    try:
        if 'file' not in request.files:
            return jsonify(create_response(error="No file part in the request")), 400

        file = request.files['file']
        keywords, blacklist = process_uploaded_file(file)

        return jsonify(create_response(
            success=True,
            data={
                "keywords": keywords,
                "blacklist": blacklist
            },
            message="Keywords and blacklist extracted successfully"
        )), 200

    except ValueError as e:
        return jsonify(create_response(error=str(e))), 400
    except Exception as e:
        return jsonify(create_response(error=f"An error occurred while processing the file: {str(e)}")), 500
