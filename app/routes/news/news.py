
# FILE DEPRACATED, SCHEDULE TO REMOVE AND DELETE AFTER articles.py is improved.


from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from http import HTTPStatus
from app.routes.routes_utils import create_response, handle_db_session
from config import Article, db

website_news_bp = Blueprint('website_news_bp', __name__, template_folder='templates', static_folder='static')

@website_news_bp.route('/api/get/latest_news', methods=['GET'])
@handle_db_session
def get_latest_news():
    """
    Retrieve the latest news articles for a specific coin bot.

    Args:
        coin_bot_id (int): The ID of the coin bot.
        limit (int, optional): The maximum number of articles to return. Defaults to 20.

    Returns:
        JSON: A list of articles or an error message.
    """
    try:
        coin_bot_id = request.args.get('coin_bot_id', type=int)
        limit = request.args.get('limit', 20, type=int)

        if coin_bot_id is None:
            response = create_response(error="Coin Bot ID is required")
            return jsonify(response), HTTPStatus.BAD_REQUEST

        start_date = datetime.now() - timedelta(days=30)

        articles = db.session.query(Article).filter(
            Article.bot_id == coin_bot_id,
            Article.created_at >= start_date
        ).order_by(desc(Article.created_at)).limit(limit).all()

        if articles:
            articles_list = [article.as_dict() for article in articles]
            response = create_response(success=True, data=articles_list)
        else:
            response = create_response(error=f"No articles found for Coin Bot {coin_bot_id} in the last 30 days")
            return jsonify(response), HTTPStatus.NOT_FOUND

    except SQLAlchemyError as e:
        response = create_response(error=f"Database error: {str(e)}")
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        response = create_response(error=f"An unexpected error occurred: {str(e)}")
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(response), HTTPStatus.OK

@website_news_bp.route('/api/get/article', methods=['GET'])
@handle_db_session
def get_article_by_id():
    """
    Retrieve a specific article by its ID.

    Args:
        article_id (int): The ID of the article to retrieve.

    Returns:
        JSON: The article data or an error message.
    """
    try:
        article_id = request.args.get('article_id', type=int)

        if article_id is None:
            response = create_response(error="Article ID is required")
            return jsonify(response), HTTPStatus.BAD_REQUEST

        article = db.session.query(Article).filter(Article.id == article_id).first()

        if article:
            article_data = article.as_dict()
            response = create_response(success=True, data=article_data)
        else:
            response = create_response(error=f"Article with ID {article_id} not found")
            return jsonify(response), HTTPStatus.NOT_FOUND

    except SQLAlchemyError as e:
        response = create_response(error=f"Database error: {str(e)}")
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        response = create_response(error=f"An unexpected error occurred: {str(e)}")
        return jsonify(response), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(response), HTTPStatus.OK
