from datetime import datetime
from math import ceil
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from app.routes.articles.utils import download_and_process_image, validate_article_creation
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from config import Article, Bot, Category, db, UnwantedArticle, UsedKeywords
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis, update_cache_with_redis

articles_bp = Blueprint('articles_bp', __name__, 
                        template_folder='templates', 
                        static_folder='static')

@articles_bp.route('/articles', methods=['GET'])
@handle_db_session
def get_articles():
    """
    Retrieve articles with advanced filtering and pagination.
    
    Query Parameters:
    - page: The page number (default: 1)
    - per_page: Number of articles per page (default: 10)
    - search: Search term to filter articles by content or title
    - bot: Filter articles by bot name
    - category: Filter articles by category name
    - top_stories: If "true", return only top stories
    - bin: If "true", include unwanted articles (default: false)
    - valid_articles: If "true", include valid articles (default: true)
    
    Returns:
        JSON response with filtered list of articles and pagination info
    """
    # Get query parameters with defaults
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_term = request.args.get('search', '').strip()
    bot_name = request.args.get('bot', '').strip()
    category_name = request.args.get('category', '').strip()
    top_stories = request.args.get('top_stories', '').lower() == 'true'
    include_bin = request.args.get('bin', '').lower() == 'true'
    include_valid = request.args.get('valid_articles', 'true').lower() == 'true'

    # Initialize queries based on flags
    queries = []
    
    if include_valid:
        article_query = (Article.query
            .outerjoin(Bot, Article.bot_id == Bot.id))

        if search_term:
            article_query = article_query.filter(
                db.or_(
                    Article.content.ilike(f'%{search_term}%'),
                    Article.title.ilike(f'%{search_term}%')
                )
            )
        if bot_name:
            article_query = article_query.filter(func.lower(Bot.name) == bot_name.lower())
        if category_name:
            article_query = article_query.filter(func.lower(Category.name) == category_name.lower())
        if top_stories:
            article_query = article_query.filter(Article.is_top_story == True)
            
        queries.append(
            article_query.with_entities(
                Article.id,
                Article.title,
                Article.content,
                Article.image,
                Article.url,
                Article.date,
                Article.bot_id,
                Article.created_at.label('created_at'),
                Article.updated_at,
                Article.is_top_story.label('top_story'),
                Bot.icon.label('bot_icon'),
                Category.name.label('category_name'),
                Category.icon.label('category_icon'),
                db.literal('valid').label('type')
            )
        )

    if include_bin:
        unwanted_query = (UnwantedArticle.query
            .outerjoin(Bot, UnwantedArticle.bot_id == Bot.id))

        if search_term:
            unwanted_query = unwanted_query.filter(
                db.or_(
                    UnwantedArticle.content.ilike(f'%{search_term}%'),
                    UnwantedArticle.title.ilike(f'%{search_term}%')
                )
            )
        if bot_name:
            unwanted_query = unwanted_query.filter(func.lower(Bot.name) == bot_name.lower())
            
        queries.append(
            unwanted_query.with_entities(
                UnwantedArticle.id,
                UnwantedArticle.title,
                UnwantedArticle.content,
                db.null().label('image'),
                UnwantedArticle.url,
                UnwantedArticle.date,
                UnwantedArticle.bot_id,
                UnwantedArticle.created_at.label('created_at'),
                UnwantedArticle.updated_at,
                db.literal(False).label('top_story'),
                Bot.icon.label('bot_icon'),
                db.null().label('category_name'),
                db.null().label('category_icon'),
                db.literal('bin').label('type')
            )
        )

    # Validate and combine queries
    if not queries:
        return jsonify(create_response(
            error='At least one article type (bin or valid_articles) must be selected'
        )), 400

    # Combine and order results
    base_query = queries[0] if len(queries) == 1 else queries[0].union(queries[1])
    base_query = base_query.order_by(desc('created_at'))

    # Handle pagination
    total_items = base_query.count()
    total_pages = ceil(total_items / per_page)

    if page < 1 or per_page < 1:
        return jsonify(create_response(
            error='Page and per_page must be positive integers'
        )), 400

    if page > total_pages and total_items > 0:
        return jsonify(create_response(
            error=f'Page {page} does not exist. Max page is {total_pages}'
        )), 404

    # Get paginated results
    items = base_query.offset((page - 1) * per_page).limit(per_page).all()

    if not items:
        return jsonify(create_response(
            success=True, 
            data=[], 
            message='No articles found'
        )), 204

    # Prepare response
    data = [{
        'id': item.id,
        'title': item.title,
        'content': item.content,
        'image': item.image,
        'url': item.url,
        'date': item.date,
        'bot_id': item.bot_id,
        'bot_icon': item.bot_icon,
        'created_at': item.created_at,
        'updated_at': item.updated_at,
        'top_story': item.top_story,
        'category_name': item.category_name,
        'category_icon': item.category_icon,
        'type': item.type
    } for item in items]

    response = create_response(
        success=True,
        data=data,
        pagination={
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_items
        }
    )
    return jsonify(response), 200

@articles_bp.route('/article/<int:article_id>', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID from either the Article or UnwantedArticle table.
    
    Returns article details in a standardized format including category and bot information.
    
    Args:
        article_id (int): The ID of the article to retrieve.
    
    Returns:
        JSON response with the article data or an error message.
    """
    # Query Article table with joins for category and bot info
    article = (Article.query
        .outerjoin(Bot, Article.bot_id == Bot.id)
        .filter(Article.id == article_id)
        .with_entities(
            Article.id,
            Article.title,
            Article.content,
            Article.image,
            Article.url,
            Article.date,
            Article.bot_id,
            Article.created_at,
            Article.updated_at,
            Article.is_top_story,
            Category.name.label('category_name'),
            Category.icon.label('category_icon'),
            Bot.icon.label('bot_icon'),
            db.literal('valid').label('type')
        ).first())
    
    if article:
        response_data = {
            'id': article.id,
            'title': article.title,
            'content': article.content,
            'image': article.image,
            'url': article.url,
            'date': article.date,
            'bot_id': article.bot_id,
            'bot_icon': article.bot_icon,
            'created_at': article.created_at,
            'updated_at': article.updated_at,
            'top_story': article.is_top_story,
            'category_name': article.category_name,
            'category_icon': article.category_icon,
            'type': article.type
        }
        response = create_response(success=True, data=response_data)
        return jsonify(response), 200
    
    # If not found in Article table, check UnwantedArticle table
    unwanted = (UnwantedArticle.query
        .outerjoin(Bot, UnwantedArticle.bot_id == Bot.id)
        .filter(UnwantedArticle.id == article_id)
        .with_entities(
            UnwantedArticle.id,
            UnwantedArticle.title,
            UnwantedArticle.content,
            UnwantedArticle.url,
            UnwantedArticle.date,
            UnwantedArticle.bot_id,
            UnwantedArticle.created_at,
            UnwantedArticle.updated_at,
            Bot.icon.label('bot_icon'),
            db.literal('bin').label('type')
        ).first())
    
    if unwanted:
        response_data = {
            'id': unwanted.id,
            'title': unwanted.title,
            'content': unwanted.content,
            'image': None,
            'url': unwanted.url,
            'date': unwanted.date,
            'bot_id': unwanted.bot_id,
            'bot_icon': unwanted.bot_icon,
            'created_at': unwanted.created_at,
            'updated_at': unwanted.updated_at,
            'top_story': False,
            'category_name': None,
            'category_icon': None,
            'type': unwanted.type
        }
        response = create_response(success=True, data=response_data)
        return jsonify(response), 200
    
    response = create_response(error='No article found for the specified article ID')
    return jsonify(response), 404


@articles_bp.route('/article', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_articles_by_bot():
    """
    Retrieve articles by bot ID or bot name with optional pagination and search functionality.
    
    Query Parameters:
    - bot_id: ID of the bot (optional if bot_name is provided)
    - bot_name: Name of the bot (optional if bot_id is provided)
    - page: The page number (optional)
    - per_page: Number of articles per page (optional)
    - search: Search term to filter articles by content (optional)
    
    Returns:
        JSON response with the list of articles, pagination info (if applicable), or an error message.
    """
    bot_id = request.args.get('bot_id', type=int)
    bot_name = request.args.get('bot_name')
    page = request.args.get('page', type=int)
    per_page = request.args.get('per_page', type=int)
    search_term = request.args.get('search', '')

    if not bot_id and not bot_name:
        return jsonify(create_response(error='Missing bot ID or bot name in request data')), 400

    if bot_name:
        bot = Bot.query.filter_by(name=bot_name).first()
        if not bot:
            return jsonify(create_response(error='No bot found with the specified bot name')), 404
        bot_id = bot.id

    if (page is not None and page < 1) or (per_page is not None and per_page < 1):
        return jsonify(create_response(error='Page and per_page must be positive integers')), 400

    query = Article.query.filter_by(bot_id=bot_id)

    if search_term:
        query = query.filter(Article.content.ilike(f'%{search_term}%'))

    query = query.order_by(desc(Article.created_at))
    
    total_articles = query.count()

    if page is None or per_page is None:
        articles = query.all()
        pagination_info = None
    else:
        total_pages = ceil(total_articles / per_page)
        if page > total_pages and total_articles > 0:
            return jsonify(create_response(error=f'Page {page} does not exist. Max page is {total_pages}')), 404

        articles = query.paginate(page=page, per_page=per_page, error_out=False).items
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_articles
        }

    if not articles:
        return jsonify(create_response(success=True, data=[], message='No articles found for the specified criteria')), 204

    response = create_response(
        success=True,
        data=[article.as_dict() for article in articles],
        pagination=pagination_info
    )
    return jsonify(response), 200



@articles_bp.route('/article/<int:article_id>', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_all_articles', 'get_article_by_id', 'get_articles_by_bot'])
@handle_db_session
def delete_article(article_id):
    """
    Delete an article by its ID.
    
    Args:
        article_id (int): The ID of the article to delete.
    
    Returns:
        JSON response with the success status or an error message.
    """
    if not article_id:
        return jsonify(create_response(error='Article ID is required')), 400

    try:
        # First delete related used keywords
        UsedKeywords.query.filter_by(article_id=article_id).delete()
        
        # Then delete the article
        article = Article.query.get(article_id)
        if not article:
            return jsonify(create_response(error='Article not found')), 404

        db.session.delete(article)
        db.session.commit()
        
        return jsonify(create_response(success=True, message='Article deleted successfully')), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(error=f'Database error: {str(e)}')), 500



@articles_bp.route('/article', methods=['POST'])
def create_article():
    """
    Create a new article with comprehensive validation and error handling.
    
    Request Body:
        - title (str, required): Article title
        - content (str, required): Article content
        - bot_id (int, required): Bot identifier
        - category_id (int, required): Category identifier
        - image_url (str, required): URL of the article image
        - comment (str, optional): Comment on the article efficiency
        - is_top_story (bool, optional): Whether this is a top story
    
    Required Parameters:
        - title
        - content
        - bot_id
        - category_id
        - image_url
    
    Returns:
        JSON response with created article data or error message
    
    Response Codes:
        201: Article created successfully
        400: Bad request (missing/invalid fields)
        409: Conflict (duplicate article)
        500: Internal server error
    """
    try:
        # Parse incoming JSON data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'image_url', 'content', 'bot_id', 'category_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify(create_response(
                error=f'Missing required fields: {", ".join(missing_fields)}'
            )), 400
        
        # Validate bot_id and category_id exist
        if not Bot.query.filter_by(id=data['bot_id']).first():
            return jsonify(create_response(
                error='Bot ID does not exist'
            )), 400
        if not Category.query.filter_by(id=data['category_id']).first():
            return jsonify(create_response(
                error='Category ID does not exist'
            )), 400
        
        # Validate input data
        validation_result = validate_article_creation(data)
        if not validation_result['valid']:
            return jsonify(create_response(
                error=validation_result['errors']
            )), 400
        
        # Check for potential duplicate article
        existing_article = Article.query.filter(
            func.lower(Article.title) == data['title'].lower()
        ).first()
        if existing_article:
            return jsonify(create_response(
                error='An article with this title already exists'
            )), 409
        
        # Download and process image
        try:
            image_filename = download_and_process_image(
                data['image_url'], 
                data['title']
            )
        except Exception as e:
            return jsonify(create_response(
                error=f'Image processing failed: {str(e)}'
            )), 400
        
        # Prepare article data
        current_time = datetime.now()
        new_article = Article(
            title=data['title'],
            content=data['content'].replace("- ", ""),
            image=image_filename,
            url="Generated By AI Alpha Team.",
            date=current_time,
            is_article_efficent='Green - ' + data.get('comment', ''),
            is_top_story=data.get('is_top_story', False), 
            bot_id=data['bot_id'],
            created_at=current_time,
            updated_at=current_time
        )
        
        # Save article to database
        try:
            db.session.add(new_article)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify(create_response(
                error=f'Database insertion failed: {str(e)}'
            )), 500
        
        # Return successful response
        return jsonify(create_response(
            success=True, 
            data=new_article.as_dict()
        )), 201
    
    except Exception as e:
        return jsonify(create_response(
            error=f'Unexpected error occurred: {str(e)}'
        )), 500


