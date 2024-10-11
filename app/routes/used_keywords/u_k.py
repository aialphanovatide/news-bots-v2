from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from app.routes.routes_utils import create_response, handle_db_session
from config import Article, UsedKeywords, db
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError


news_bots_features_bp = Blueprint(
    'news_bots_features_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@news_bots_features_bp.route('/keywords/trending', methods=['GET'])
@handle_db_session
def get_used_keywords():
    """
    Retrieves used keywords with optional filtering by bot_id and time period.
    Also provides a count of keyword usage.

    Query Parameters:
    - bot_id (int, optional): Bot ID to filter keywords.
    - time_period (str, optional): Time period for filtering ("1w", "1m", "3m", "all"). Default is "all".

    Returns:
        JSON: Response with used keywords, their usage count, and optional filtering information.
    """
    try:
        bot_id = request.args.get('bot_id', type=int)
        time_period = request.args.get('time_period', default='all')

        query = db.session.query(UsedKeywords.keywords, func.count(UsedKeywords.id).label('count'))

        if bot_id:
            query = query.filter(UsedKeywords.bot_id == bot_id)

        if time_period != 'all':
            end_date = datetime.now()
            if time_period == "1w":
                start_date = end_date - timedelta(weeks=1)
            elif time_period == "1m":
                start_date = end_date - timedelta(days=30)
            elif time_period == "3m":
                start_date = end_date - timedelta(days=90)
            else:
                return jsonify(create_response(error=f'Invalid time period: {time_period}')), 400
            
            query = query.filter(UsedKeywords.article_date.between(start_date, end_date))

        results = query.group_by(UsedKeywords.keywords).order_by(func.count(UsedKeywords.id).desc()).all()

        if not results:
            return jsonify(create_response(message='No keywords found', data={'used_keywords': []})), 200

        used_keywords_list = []
        for keywords, count in results:
            # Split the keywords string into individual keywords
            keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
            for keyword in keyword_list:
                used_keywords_list.append({'keyword': keyword, 'count': count})

        # Aggregate counts for duplicate keywords
        keyword_counts = {}
        for item in used_keywords_list:
            keyword = item['keyword']
            count = item['count']
            if keyword in keyword_counts:
                keyword_counts[keyword] += count
            else:
                keyword_counts[keyword] = count

        # Create the final list of unique keywords with their total counts
        final_keyword_list = [{'keyword': k, 'count': v} for k, v in keyword_counts.items()]
        final_keyword_list.sort(key=lambda x: x['count'], reverse=True)

        response = create_response(
            success=True,
            message='Used keywords retrieved successfully',
            data={
                'used_keywords': final_keyword_list,
                'total_unique_keywords': len(final_keyword_list),
                'filter_applied': {
                    'bot_id': bot_id,
                    'time_period': time_period
                }
            }
        )
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500
    
    except Exception as e:
        return jsonify(create_response(error=f'Internal server error: {str(e)}')), 500