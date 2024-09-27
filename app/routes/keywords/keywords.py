# routes.py

# FILE DEPRACATED, SCHEDULE TO REMOVE AND DELETE AFTER SERVER UPDATE

from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Blacklist, Keyword, db
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

keyword_bp = Blueprint(
    'keyword_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@keyword_bp.route('/get_keywords', methods=['GET'])
@measure_execution_time
@handle_db_session
def get_keywords_by_bot():
    """
    Get all keywords filtered by bot_id.
    Args:
        bot_id (int): Bot ID to filter keywords.
    Response:
        200: Successfully retrieved keywords.
        400: Bot ID missing in request parameters.
        404: No keywords found for the provided bot ID.
        500: Internal server error or database error.
    """
    try:
        bot_id = request.args.get('bot_id')

        if not bot_id:
            response = create_response(error='Bot ID missing in request parameters')
            return jsonify(response), 400

        keywords = Keyword.query.filter_by(bot_id=bot_id).all()

        if not keywords:
            response = create_response(error='No keywords found for the provided bot ID')
            return jsonify(response), 404

        keyword_data = [key.as_dict() for key in keywords]

        response = create_response(success=True, data=keyword_data)
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@keyword_bp.route('/add_keyword', methods=['POST'])
@measure_execution_time
@handle_db_session
def add_keyword_to_bot():
    """
    Add keyword(s) to a bot.
    Data:
        JSON data with 'keyword' (str) and 'bot_id' (int).
    Response:
        200: Keywords added to bot successfully or no new keywords added.
        400: Keyword or Bot ID missing in request data.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        keyword = data.get('keyword')
        bot_id = data.get('bot_id')

        if not keyword or not bot_id:
            response = create_response(error='Keyword or Bot ID missing in request data')
            return jsonify(response), 400

        keywords = [keyword.strip() for keyword in keyword.split(',')]

        # Get existing keywords for the specified bot
        existing_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
        existing_keyword_names = [kw.name.lower() for kw in existing_keywords]

        new_keywords = []
        current_time = datetime.now()

        # Filter out duplicate keywords
        for kw in keywords:
            if kw.lower() not in existing_keyword_names:
                new_keywords.append(Keyword(name=kw, bot_id=bot_id, created_at=current_time, updated_at=current_time))

        # Add new keywords to the database
        if new_keywords:
            db.session.add_all(new_keywords)
            db.session.commit()
            response = create_response(success=True, message='Keywords added to bot successfully')
            return jsonify(response), 200
        else:
            response = create_response(success=True, message='No new keywords added')
            return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@keyword_bp.route('/delete_keyword', methods=['DELETE'])
@measure_execution_time
@handle_db_session
def delete_keyword_from_bot():
    """
    Delete a keyword from a bot by ID.
    Args:
        keyword_id (int): ID of the keyword to delete.
    Response:
        200: Keyword deleted from bot successfully.
        400: Keyword ID missing in request data.
        404: Keyword not found.
        500: Internal server error or database error.
    """
    try:
        keyword_id = request.args.get('keyword_id')

        if keyword_id is None:
            response = create_response(error='Keyword ID missing in request data')
            return jsonify(response), 400

        keyword = Keyword.query.get(keyword_id)
        if keyword:
            db.session.delete(keyword)
            db.session.commit()
            response = create_response(success=True, message='Keyword deleted from bot successfully')
            return jsonify(response), 200
        else:
            response = create_response(error='Keyword not found')
            return jsonify(response), 404

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@keyword_bp.route('/get_keywords_for_coin_bot/<int:coin_bot_id>', methods=['GET'])
def get_keywords_for_coin_bot(coin_bot_id):
    """
    Get all keywords for a coin bot by bot_id.
    Args:
        coin_bot_id (int): Bot ID to filter keywords.
    Response:
        200: Successfully retrieved keywords for the coin bot.
        500: Internal server error or database error.
    """
    try:
        keywords = db.session.query(Keyword).filter_by(bot_id=coin_bot_id).all()
        keywords_data = [{'id': keyword.id, 'word': keyword.name} for keyword in keywords]
        response = create_response(success=True, data=keywords_data)
        return jsonify(response), 200

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500



@keyword_bp.route('/keywords_dinamic_search', methods=['GET'])
@measure_execution_time
@handle_db_session
def dynamic_search():
    """
    Search for related keywords and backlist words.
    Args:
        query (str): Word to search.
    Response:
        200: Successfully retrieved relevant words.
        400: Missing query parameter.
        404: No related words found.
        500: Server error.
    """
    try:
        query = request.args.get('query')

        if not query:
            return jsonify(create_response(error='Query string missing in request parameters')), 400

        # Conduct search through the keyword and backlist tables
        keyword_results = Keyword.query.filter(Keyword.name.ilike(f'%{query}%')).all()
        backlist_results = Blacklist.query.filter(Blacklist.name.ilike(f'%{query}%')).all()

        if not keyword_results and not backlist_results:
            return jsonify(create_response(error='No related words found')), 404

        # Prepare results
        related_words = [kw.name for kw in keyword_results] + [bl.word for bl in backlist_results]

        return jsonify(create_response(success=True, data=related_words)), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500

    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500