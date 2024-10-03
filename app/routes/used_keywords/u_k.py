from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from app.routes.routes_utils import create_response, handle_db_session
from config import Article, UsedKeywords, db
from sqlalchemy.exc import SQLAlchemyError


news_bots_features_bp = Blueprint(
    'news_bots_features_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@news_bots_features_bp.route('/api/get_used_keywords_to_download', methods=['GET'])

@handle_db_session
def get_used_keywords_to_download():
    """
    Retrieves used keywords from articles based on a specified time period and bot ID.

    Args:
        bot_id (int): Bot ID to filter articles.
        time_period (str): Time period for filtering articles ("1w", "1m", "3m").

    Returns:
        JSON: Response with unique keywords extracted from articles or error message.
    """
    try:
        response = create_response(message='Keywords retrieved successfully')
        
        bot_id = request.args.get('bot_id', type=int)
        time_period = request.args.get('time_period', default='3d')

        end_date = datetime.now()
        if time_period == "1w":
            start_date = end_date - timedelta(weeks=1)
        elif time_period == "1m":
            start_date = end_date - timedelta(days=30)
        elif time_period == "3m":
            start_date = end_date - timedelta(days=90)
        else:
            response = create_response(error=f'Invalid time period: {time_period}')
            return jsonify(response), 400

        articles_query = db.session.query(Article.used_keywords).filter(
            Article.bot_id == bot_id,
            Article.created_at >= start_date,
            Article.created_at <= end_date
        ).all()

        all_keywords = ' '.join([article.used_keywords for article in articles_query if article.used_keywords])
        unique_keywords = list(set(all_keywords.split(', ')))
        unique_keywords.sort()

        response['data'] = {"keywords": unique_keywords}
        response['success'] = True
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500
    
    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@news_bots_features_bp.route('/api/get/used_keywords', methods=['GET'])

@handle_db_session
def get_used_keywords():
    """
    Retrieves all used keywords stored in the database.

    Returns:
        JSON: Response with used keywords or a message indicating none were found.
    """
    try:
        response = create_response(message='Used keywords retrieved successfully')

        used_keywords = db.session.query(UsedKeywords).all()

        if not used_keywords:
            response = create_response(error='No keywords found')
            return jsonify(response), 404
        else:
            used_keywords_list = [keyword.as_dict() for keyword in used_keywords]
            response['data'] = {'used_keywords': used_keywords_list}
            response['success'] = True
            return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500
    
    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500
