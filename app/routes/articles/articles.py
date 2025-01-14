from datetime import datetime
from math import ceil
import os
from werkzeug.utils import secure_filename
from sqlalchemy import desc, func, literal_column
from sqlalchemy.exc import SQLAlchemyError
from flask import Blueprint, jsonify, request
from app.routes.articles.utils import download_and_process_image, validate_article_creation, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, allowed_file
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.services.news_creator.news_creator import NewsCreatorAgent
from config import Article, Bot, Category, db, UnwantedArticle, UsedKeywords, ArticleTimeframe
from app.routes.routes_utils import create_response, handle_db_session
from redis_client.redis_client import cache_with_redis, update_cache_with_redis

articles_bp = Blueprint('articles_bp', __name__, 
                        template_folder='templates', 
                        static_folder='static')


@articles_bp.route('/articles', methods=['GET'])
@handle_db_session
def get_all_articles_all():
    """
    Retrieve articles with advanced filtering and pagination.
    
    Query Parameters:
    - page: The page number (default: 1)
    - per_page: Number of articles per page (default: 10)
    - search: Search term to filter articles by content or title
    - bot_name: Filter articles by bot name (case insensitive)
    - category_name: Filter articles by category name (case insensitive)
    - top_stories: If "true", return top stories
    - timeframe: Filter top stories by timeframe ('1D', '1W', '1M')
    - bin: If "true", include unwanted articles
    - valid_articles: If "true", include valid articles
    """
    try:
        # Get query parameters with defaults
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search_term = request.args.get('search', '').strip()
        bot_name = request.args.get('bot_name', '').strip()
        category_name = request.args.get('category_name', '').strip()
        top_stories = request.args.get('top_stories', '').lower() == 'true'
        timeframe = request.args.get('timeframe')
        include_bin = request.args.get('bin', '').lower() == 'true'
        include_valid = request.args.get('valid_articles', 'true').lower() == 'true'

        # Validate parameters
        if page < 1 or per_page < 1:
            return jsonify(create_response(
                error='Page and per_page must be positive integers'
            )), 400

        if timeframe and timeframe not in ['1D', '1W', '1M']:
            return jsonify(create_response(
                error=f"Invalid timeframe: {timeframe}. Must be one of: 1D, 1W, 1M"
            )), 400

        # Initialize queries list
        queries = []

        # Handle top stories query
        if top_stories:
            top_stories_query = db.session.query(
                Article.id,
                Article.title,
                Article.content,
                Article.url,
                Article.date,
                Article.bot_id,
                Article.created_at.label('created_at'),  # Add label for ordering
                Article.updated_at,
                Article.image,
                Article.analysis,
                Article.used_keywords,
                Article.is_article_efficent,
                Article.is_top_story
            ).filter(Article.is_top_story == True)
            
            if bot_name:
                top_stories_query = top_stories_query.join(Bot).filter(func.lower(Bot.name) == bot_name.lower())
            if category_name:
                top_stories_query = top_stories_query.join(Bot).join(Category, Bot.category_id == Category.id)\
                    .filter(func.lower(Category.name) == category_name.lower())
            if search_term:
                top_stories_query = top_stories_query.filter(
                    db.or_(
                        Article.content.ilike(f'%{search_term}%'),
                        Article.title.ilike(f'%{search_term}%')
                    )
                )
            if timeframe:
                top_stories_query = top_stories_query.join(Article.timeframes).filter(
                    ArticleTimeframe.timeframe == timeframe
                )
            
            queries.append(top_stories_query)

        # Handle valid articles query (excluding top stories)
        if include_valid and not top_stories:
            valid_query = db.session.query(
                Article.id,
                Article.title,
                Article.content,
                Article.url,
                Article.date,
                Article.bot_id,
                Article.created_at.label('created_at'),  # Add label for ordering
                Article.updated_at,
                Article.image,
                Article.analysis,
                Article.used_keywords,
                Article.is_article_efficent,
                Article.is_top_story
            ).filter(Article.is_top_story == False)
            
            if bot_name:
                valid_query = valid_query.join(Bot).filter(func.lower(Bot.name) == bot_name.lower())
            if category_name:
                valid_query = valid_query.join(Bot).join(Category, Bot.category_id == Category.id)\
                    .filter(func.lower(Category.name) == category_name.lower())
            if search_term:
                valid_query = valid_query.filter(
                    db.or_(
                        Article.content.ilike(f'%{search_term}%'),
                        Article.title.ilike(f'%{search_term}%')
                    )
                )
            
            queries.append(valid_query)

        # Handle unwanted articles query
        if include_bin:
            unwanted_query = db.session.query(
                UnwantedArticle.id,
                UnwantedArticle.title,
                UnwantedArticle.content,
                UnwantedArticle.url,
                UnwantedArticle.date,
                UnwantedArticle.bot_id,
                UnwantedArticle.created_at.label('created_at'),
                UnwantedArticle.updated_at,
                literal_column("NULL").label('image'),
                literal_column("NULL").label('analysis'),
                literal_column("NULL").label('used_keywords'),
                literal_column("NULL").label('is_article_efficent'),
                literal_column("FALSE").label('is_top_story')
            )
            
            if bot_name:
                unwanted_query = unwanted_query.join(Bot).filter(func.lower(Bot.name) == bot_name.lower())
            if category_name:
                unwanted_query = unwanted_query.join(Bot).join(Category, Bot.category_id == Category.id)\
                    .filter(func.lower(Category.name) == category_name.lower())
            if search_term:
                unwanted_query = unwanted_query.filter(
                    db.or_(
                        UnwantedArticle.content.ilike(f'%{search_term}%'),
                        UnwantedArticle.title.ilike(f'%{search_term}%')
                    )
                )
            
            queries.append(unwanted_query)

        # Ensure at least one type of article is being queried
        if not queries:
            return jsonify(create_response(
                error='At least one article type must be selected'
            )), 400

        # Combine queries and add ordering
        base_query = queries[0].union(*queries[1:]) if len(queries) > 1 else queries[0]
        base_query = base_query.order_by(desc('created_at'))

        # Get pagination info
        total_items = base_query.count()
        total_pages = ceil(total_items / per_page)

        if page > total_pages and total_items > 0:
            return jsonify(create_response(
                error=f'Page {page} does not exist. Max page is {total_pages}'
            )), 404

        # Get paginated items
        items = base_query.offset((page - 1) * per_page).limit(per_page).all()

        if not items:
            return jsonify(create_response(
                success=True,
                data=[],
                message='No articles found'
            )), 204

        # Convert items to dictionaries
        data = []
        for item in items:
            item_dict = {
                'id': item[0],
                'title': item[1],
                'content': item[2],
                'url': item[3],
                'date': item[4],
                'bot_id': item[5],
                'created_at': item[6],
                'updated_at': item[7],
                'image': item[8],
                'analysis': item[9],
                'used_keywords': item[10],
                'is_article_efficent': item[11],
                'is_top_story': item[12],
                'timeframes': []  # Will be populated for top stories
            }
            
            # Add timeframes for top stories
            if item[12]:  # is_top_story
                timeframes = ArticleTimeframe.query.filter_by(article_id=item[0]).all()
                item_dict['timeframes'] = [tf.as_dict() for tf in timeframes]
            
            data.append(item_dict)

        return jsonify(create_response(
            success=True,
            data=data,
            pagination={
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'total_items': total_items
            },
            filters={
                'bot_name': bot_name or None,
                'category_name': category_name or None,
                'timeframe': timeframe or None
            }
        )), 200

    except Exception as e:
        print(f"Error in get_all_articles_all: {str(e)}")
        return jsonify(create_response(
            error=f"An unexpected error occurred: {str(e)}"
        )), 500

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


@articles_bp.route('/article/<int:article_id>', methods=['DELETE'])
@update_cache_with_redis(related_get_endpoints=['get_all_articles', 'get_article_by_id', 'get_articles_by_bot'])
@handle_db_session
def delete_article(article_id):
    """
    Delete an article by its ID and its associated data (timeframes and keywords).
    
    This endpoint removes an article and all its related data from the database.
    If the article is a top story, it will also remove associated timeframes.
    
    Args:
        article_id (int): The ID of the article to delete.
    
    Returns:
        JSON response with:
            - success (bool): Indicates if the operation was successful
            - message (str): A success message
            - error (str, optional): Error message if operation failed
    """
    if not article_id:
        return jsonify(create_response(
            error='Article ID is required'
        )), 400

    try:
        # First check if article exists
        article = Article.query.get(article_id)
        if not article:
            return jsonify(create_response(
                error='Article not found'
            )), 404

        # Delete related timeframes if article is a top story
        if article.is_top_story:
            ArticleTimeframe.query.filter_by(article_id=article_id).delete()

        # Delete related used keywords
        UsedKeywords.query.filter_by(article_id=article_id).delete()
        print(f"Deleted keywords for article {article_id}")
        
        # Finally delete the article
        db.session.delete(article)
        db.session.commit()
        
        return jsonify(create_response(
            success=True, 
            message='Article and its associated data deleted successfully'
        )), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(create_response(
            error=f'Database error: {str(e)}'
        )), 500
    except Exception as e:
        db.session.rollback()
        return jsonify(create_response(
            error=f'An unexpected error occurred: {str(e)}'
        )), 500


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
        - timeframes (list, required if is_top_story=True): List of timeframes ('1D', '1W', '1M')
    
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
        
        # Validate timeframes if is_top_story is True
        is_top_story = data.get('is_top_story', False)
        timeframes = data.get('timeframes', [])
        
        if is_top_story and not timeframes:
            return jsonify(create_response(
                error='Timeframes are required when is_top_story is True'
            )), 400
            
        if timeframes:
            valid_timeframes = ['1D', '1W', '1M']
            invalid_timeframes = [tf for tf in timeframes if tf not in valid_timeframes]
            if invalid_timeframes:
                return jsonify(create_response(
                    error=f'Invalid timeframes: {", ".join(invalid_timeframes)}. Must be one of: {", ".join(valid_timeframes)}'
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
            content=data['content'],
            image=image_filename,
            url="Generated By AI Alpha Team.",
            date=current_time,
            is_article_efficent='Green - ' + data.get('comment', ''),
            is_top_story=is_top_story,
            bot_id=data['bot_id'],
            created_at=current_time,
            updated_at=current_time
        )
        
        # Add timeframes if is_top_story
        if is_top_story:
            for timeframe in timeframes:
                new_timeframe = ArticleTimeframe(
                    timeframe=timeframe,
                    created_at=current_time,
                    updated_at=current_time
                )
                new_article.timeframes.append(new_timeframe)
        
        # Save to database
        try:
            db.session.add(new_article)
            db.session.commit()
            
            return jsonify(create_response(
                success=True, 
                data=new_article.as_dict()
            )), 201
            
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(create_response(
                error=f'Database insertion failed: {str(e)}'
            )), 500
    
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
