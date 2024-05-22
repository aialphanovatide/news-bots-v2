from flask import Blueprint, jsonify, request
from config import Keyword, db
from datetime import datetime

keyword_bp = Blueprint(
    'keyword_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get all keywords filtered by bot_id
@keyword_bp.route('/get_keywords', methods=['GET'])
def get_keywords_by_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')

        if not bot_id:
            response['error'] = 'Bot ID missing in request parameters'
            return jsonify(response), 400

        keywords = Keyword.query.filter_by(bot_id=bot_id).all()

        if not keywords:
            response['error'] = 'No keywords found for the provided bot ID'
            return jsonify(response), 404

        keyword_data = [key.as_dict() for key in keywords]

        response['data'] = keyword_data
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500




# Add keyword(s) to a bot
@keyword_bp.route('/add_keyword', methods=['POST'])
def add_keyword_to_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        data = request.json
        keyword = data.get('keyword')
        bot_id = data.get('bot_id')

        if not keyword or not bot_id:
            response['error'] = 'Keyword or Bot ID missing in request data'
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
            response['message'] = 'Keywords added to bot successfully'
            response['success'] = True
            return jsonify(response), 200
        else:
            response['message'] = 'No new keywords added'
            return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500



# Delete a keyword from a bot by ID
@keyword_bp.route('/delete_keyword', methods=['DELETE'])
def delete_keyword_from_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        keyword_id = request.args.get('keyword_id')

        if keyword_id is None:
            response['error'] = 'Keyword ID missing in request data'
            return jsonify(response), 400

        keyword = Keyword.query.get(keyword_id)
        if keyword:
            db.session.delete(keyword)
            db.session.commit()
            response['message'] = 'Keyword deleted from bot successfully'
            response['success'] = True
            return jsonify(response), 200
        else:
            response['error'] = 'Keyword not found'
            return jsonify(response), 404
    except Exception as e:
        db.session.rollback()
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500

