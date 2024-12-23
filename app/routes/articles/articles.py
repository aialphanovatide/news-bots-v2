from datetime import datetime
from math import ceil
import os
from werkzeug.utils import secure_filename
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from app.routes.articles.utils import download_and_process_image, validate_article_creation, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, allowed_file
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.services.news_creator.news_creator import NewsCreatorAgent
from config import Article, Bot, Category, db, UnwantedArticle, UsedKeywords
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis, update_cache_with_redis

articles_bp = Blueprint('articles_bp', __name__, 
                        template_folder='templates', 
                        static_folder='static')

@articles_bp.route('/articles/all', methods=['GET'])
@handle_db_session
def get_all_articles_all():
    """
    Retrieve articles with advanced filtering and pagination.
    
    Query Parameters:
    - page: The page number (default: 1)
    - per_page: Number of articles per page (default: 10)
    - search: Search term to filter articles by content or title
    - bot_id: Filter articles by specific bot
    - top_stories: If "true", return only top stories
    - bin: If "true", include unwanted articles
    - valid_articles: If "true", include valid articles
    
    Returns:
        JSON response with filtered list of articles and pagination info
    """
    # Get query parameters with defaults
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_term = request.args.get('search', '').strip()
    bot_id = request.args.get('bot_id', type=int)
    top_stories = request.args.get('top_stories', '').lower() == 'true'
    include_bin = request.args.get('bin', '').lower() == 'true'
    include_valid = request.args.get('valid_articles', 'true').lower() == 'true'  # defaults to true

    # Validate pagination parameters
    if page < 1 or per_page < 1:
        response = create_response(error='Page and per_page must be positive integers')
        return jsonify(response), 400

    # Special handling for top stories request
    if top_stories:
        base_query = Article.query.filter(Article.is_top_story == True)
        
        if search_term:
            base_query = base_query.filter(
                db.or_(
                    Article.content.ilike(f'%{search_term}%'),
                    Article.title.ilike(f'%{search_term}%')
                )
            )
        if bot_id:
            base_query = base_query.filter(Article.bot_id == bot_id)
            
        base_query = base_query.with_entities(
            Article.id,
            Article.title,
            Article.content,
            Article.image,
            Article.url,
            Article.date,
            Article.bot_id,
            Article.created_at.label('created_at'),
            Article.updated_at,
            Article.is_top_story,
            db.literal('valid').label('type')
        ).order_by(desc(Article.created_at))
        
    else:
        # Validate that at least one type of article is selected for non-top-stories requests
        if not include_bin and not include_valid:
            response = create_response(error='At least one article type (bin or valid_articles) must be selected')
            return jsonify(response), 400

        # Initialize queries based on flags
        queries = []
        
        if include_valid:
            article_query = Article.query
            if search_term:
                article_query = article_query.filter(
                    db.or_(
                        Article.content.ilike(f'%{search_term}%'),
                        Article.title.ilike(f'%{search_term}%')
                    )
                )
            if bot_id:
                article_query = article_query.filter(Article.bot_id == bot_id)
            
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
                    Article.is_top_story,
                    db.literal('valid').label('type')
                )
            )

        if include_bin:
            unwanted_query = UnwantedArticle.query
            if search_term:
                unwanted_query = unwanted_query.filter(
                    db.or_(
                        UnwantedArticle.content.ilike(f'%{search_term}%'),
                        UnwantedArticle.title.ilike(f'%{search_term}%')
                    )
                )
            if bot_id:
                unwanted_query = unwanted_query.filter(UnwantedArticle.bot_id == bot_id)
                
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
                    db.literal(False).label('is_top_story'),
                    db.literal('bin').label('type')
                )
            )

        # Combine queries if both types are selected
        if len(queries) > 1:
            base_query = queries[0].union(queries[1])
        else:
            base_query = queries[0]

        # Order combined results
        base_query = base_query.order_by(desc('created_at'))

    # Get total count for pagination
    total_items = base_query.count()
    total_pages = ceil(total_items / per_page)

    # Validate page number against total pages
    if page > total_pages and total_items > 0:
        response = create_response(error=f'Page {page} does not exist. Max page is {total_pages}')
        return jsonify(response), 404

    # Apply pagination
    items = base_query.offset((page - 1) * per_page).limit(per_page).all()
    if not items:
        response = create_response(success=True, data=[], message='No articles found')
        return jsonify(response), 204

    # Prepare pagination info
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_items': total_items
    }

    # Prepare response data
    data = [{
        'id': item.id,
        'title': item.title,
        'content': item.content,
        'image': item.image,
        'url': item.url,
        'date': item.date,
        'bot_id': item.bot_id,
        'created_at': item.created_at,
        'updated_at': item.updated_at,
        'is_top_story': item.is_top_story if hasattr(item, 'is_top_story') else False,
        'type': item.type
    } for item in items]

    # Prepare response
    response = create_response(
        success=True,
        data=data,
        pagination=pagination_info
    )
    return jsonify(response), 200


@articles_bp.route('/article/<int:article_id>', methods=['GET'])
@handle_db_session
@cache_with_redis()
def get_article_by_id(article_id):
    """
    Retrieve a specific article by its ID from either the Article or UnwantedArticle table.
    
    This function queries the database for an article with the specified ID in both the Article
    and UnwantedArticle tables. It returns the article details if found in either table.
    If the article is not found in either table, it returns an error response.
    
    Args:
        article_id (int): The ID of the article to retrieve.
    
    Returns:
        JSON response with the article data or an error message.
    """
    article = Article.query.filter_by(id=article_id).first()
    
    if article:
        response = create_response(success=True, data=article.as_dict(), source="Article")
        return jsonify(response), 200
    
    unwanted_article = UnwantedArticle.query.filter_by(id=article_id).first()
    
    if unwanted_article:
        response = create_response(success=True, data=unwanted_article.as_dict(), source="UnwantedArticle")
        return jsonify(response), 200
    
    response = create_response(error='No article found for the specified article ID in either Article or UnwantedArticle table')
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


@articles_bp.route('/article/generate', methods=['POST'])
def generate_article():
    """
    Generate a new article using the NewsCreatorAgent.
    
    Request Body (multipart/form-data):
        - initial_story (str, optional): Initial story or URL to generate from
        - files (files, optional): Multiple document files (PDF, DOC, DOCX, TXT)
        
    Returns:
        JSON response with the generated article content or error message
    """
    try:
        initial_story = request.form.get('initial_story')
        files = request.files.getlist('files')

        print(f"Initial story: {initial_story}")
        print(f"Files: {files}")
        
        # Validate that at least one source is provided
        if not initial_story and not files:
            return jsonify(create_response(
                error='Either initial_story or files must be provided'
            )), 400
        
        # Initialize the NewsCreatorAgent
        agent = NewsCreatorAgent(api_key=os.getenv("NEWS_BOT_OPENAI_API_KEY"))
        
        # Validate and process files
        valid_files = []
        for file in files:
            if not file.filename:
                continue
                
            # Check file extension
            file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_extension not in agent.supported_extensions:
                return jsonify(create_response(
                    error=f'Invalid file type: {file.filename}. Allowed types are: {", ".join(agent.supported_extensions)}'
                )), 400
            
            # Check file size
            file.seek(0, os.SEEK_END)
            size_mb = file.tell() / (1024 * 1024)
            file.seek(0)
            
            if size_mb > agent.MAX_FILE_SIZE_MB:
                return jsonify(create_response(
                    error=f'File too large: {file.filename} ({size_mb:.2f} MB). Maximum allowed size is {agent.MAX_FILE_SIZE_MB} MB.'
                )), 400
            
            valid_files.append(file)
        
        # Generate the story
        generated_story = agent.create_news_story(
            initial_story=initial_story,
            files=valid_files
        )
        
        if not generated_story:
            return jsonify(create_response(
                error='Failed to generate article content'
            )), 500
            
        return jsonify(create_response(
            success=True,
            data={'content': generated_story}
        )), 200
        
    except ValueError as e:
        return jsonify(create_response(
            error=f'Invalid input: {str(e)}'
        )), 400
    except Exception as e:
        return jsonify(create_response(
            error=f'Unexpected error occurred: {str(e)}'
        )), 500