from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from config import Article, UsedKeywords, db
from sqlalchemy.exc import SQLAlchemyError

news_bots_features_bp = Blueprint(
    'news_bots_features_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@news_bots_features_bp.route('/api/get_used_keywords_to_download', methods=['GET'])
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
            return jsonify({"error": "Invalid time period provided"}), 400

        # Query articles and extract used keywords within the specified time frame
        articles_query = db.session.query(Article.used_keywords).filter(
            Article.bot_id == bot_id,
            Article.created_at >= start_date,
            Article.created_at <= end_date
        ).all()

        # Unify all keywords into a single string
        all_keywords = ' '.join([article.used_keywords for article in articles_query if article.used_keywords])

        # Split the string into a list of unique keywords
        unique_keywords = list(set(all_keywords.split(', ')))

        # Optional: Sort the keywords alphabetically if desired
        unique_keywords.sort()

        return jsonify({"keywords": unique_keywords}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@news_bots_features_bp.route('/api/get/used_keywords', methods=['GET'])
def get_used_keywords():
    """
    Retrieves all used keywords stored in the database.

    Returns:
        JSON: Response with used keywords or a message indicating none were found.
    """
    try:
        # Query all used keywords from the database
        used_keywords = db.session.query(UsedKeywords).all()

        # If no used keywords found, return a 204 message with a JSON response
        if not used_keywords:
            return jsonify({'used_keywords': 'No used keywords found'}), 204
        else:
            # Convert UsedKeywords objects to dictionaries and append them to a list
            used_keywords_list = [keyword.as_dict() for keyword in used_keywords]
            # Return the list of used keywords in JSON format with a 200 status code
            return jsonify({'used_keywords': used_keywords_list}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'An error occurred getting the used keywords: {str(e)}'}), 500
