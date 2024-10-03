from datetime import datetime
from typing import Any, Dict, List
import re
from app.utils.similarity import cosine_similarity_with_openai_classification
from config import Article, Blacklist, Keyword, Session, UnwantedArticle
from app.news_bot.webscrapper.data_manager import DataManager


def datetime_checker(date):
    # Implement datetime checking logic
    pass

def last_10_article_checker(bot_id: int, article_content: str, title: str, url: str) -> Dict[str, Any]:
    """
    Check if the given article content is similar to any of the last 10 articles for a specific bot.

    Args:
        bot_id (int): The ID of the bot.
        article_content (str): The content of the article to check.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the check:
            - 'error' (str or None): Description of the error if the article is too similar.
            - 'articles_saved' (Article or None): The saved article if it's not similar.
            - 'unwanted_articles_saved' (int): The total number of unwanted articles saved.

    Raises:
        Exception: If an error occurs during the similarity check.
    """
    with Session() as session:
        data_manager=DataManager()
        # Ensure article_content is a single string
        if isinstance(article_content, list):
            article_content = " ".join(article_content)

        # Retrieve the last 10 articles
        last_10_articles: List[Article] = Article.query.filter_by(bot_id=bot_id).order_by(Article.date.desc()).limit(10).all()
        last_10_contents: List[str] = [article.content for article in last_10_articles]

        unwanted_articles_saved = 0
        is_similar = False

        # Check for high similarity using OpenAI cosine similarity function
        for content in last_10_contents:
            try:
                similarity_score = cosine_similarity_with_openai_classification(content, article_content)
                if similarity_score >= 0.9:
                    data_manager.save_unwanted_article(title=title, content=content, reason="Article is too similar to a recent article", url=url, date=datetime.now(),bot_id=bot_id,created_at=datetime.now(),updated_at=datetime.now()),
                    unwanted_articles_saved += 1
                    is_similar = True
                    break  
            except Exception as e:
                print(f"[ERROR] Exception occurred during similarity check: {str(e)}")
                raise

        # Prepare the return dictionary
        result = {
            'unwanted_articles_saved': unwanted_articles_saved
        }

        if is_similar:
            result['error'] = f"Article is too similar to a recent article (similarity score: {similarity_score})"
            result['articles_saved'] = None
        else:
            result['error'] = None
            result['articles_saved'] = None  # You might want to save the article here if it's not similar

        return result


def url_checker(url: str, bot_id: int) -> dict:
    """
    Check if a URL has been previously analyzed and stored in the database.

    This function implements the DRY (Don't Repeat Yourself) principle by centralizing
    the URL checking logic, preventing duplicates in the database. It also follows
    the SOLID principle of Single Responsibility, as it focuses solely on URL verification.

    Args:
        url (str): The URL of the article to check.
        db_connection: Database connection (assumed to be a SQLAlchemy session).

    Returns:
        dict: A dictionary containing information about the check result:
              - 'error': String with an error message if the URL was already analyzed.
              - 'articles_saved': Number of articles saved (0 in this case).
              - 'unwanted_articles_saved': Number of unwanted articles saved (0 in this case).
              Returns None if the URL hasn't been analyzed before.

    Detail:
        The function first checks if the URL exists in the UnwantedArticle table,
        then in the Article table. If found in either, it returns a dictionary
        indicating the article has already been analyzed. This approach uses the
        "Fail Fast" principle, avoiding unnecessary processing. If the URL is not
        found, the function returns None, indicating a new, unanalyzed URL.
    """
    # Check if URL has been analyzed before
    existing_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, url=url).first()
    existing_article = Article.query.filter_by(bot_id=bot_id, url=url).first()
    
    if existing_unwanted_article or existing_article:
        print(f"[INFO] Article already analyzed: {url}")
        return {
            'error': 'article already analyzed',
            'articles_saved': 0,
            'unwanted_articles_saved': 0
        }
    
    return None  # URL hasn't been analyzed before


def filter_link(url: str, exclude_terms: List[str] = ['privacy-policy', 'glossary', 'careers', 'about', 'newsletter', '/events/',
                'discord.com', 'tiktok.com', 'b1.com', 'youtube.com', 'yahoo.com', 'https://uk.movies.yahoo.com', 'uk.movies.yahoo.com',
                'advertise', 'contact-us', 'cookie-policy', 'terms-of-service', 'sirwin', 'bs3', '/tag/', '/learn/']) -> dict:
    try:
        # Check if input is valid
        if not url or not isinstance(url, str):
            raise ValueError("Invalid input. Please provide a valid URL string")
        
        if not exclude_terms or not isinstance(exclude_terms, list):
            raise ValueError("Invalid input. Please provide a non-empty list of exclude terms")

        # Define regex patterns
        social_media_regex = r'(facebook\.com|twitter\.com|linkedin\.com|instagram\.com|sponsored)'
        telegram_regex = r't\.me'

        # Check if URL passes all filters
        if (url.strip() != '' and
            not any(term in url for term in exclude_terms) and
            not re.search(social_media_regex, url) and
            not re.search(telegram_regex, url)):
            return {'response': url}
        else:
            return {'response': None}

    except ValueError as e:
        return {'error': f'Value error: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}


def keywords_filter(bot_id: int, article_content: str, article_title: str, news_link: str) -> Dict[str, Any]:
    """
    Filter articles based on keywords and blacklist keywords associated with a specific bot.

    Args:
        bot_id (int): The ID of the bot.
        article_content (str): The content of the article to check.
        article_title (str): The title of the article.
        news_link (str): The URL of the article.

    Returns:
        Dict[str, Any]: A dictionary containing the result of the filter:
            - 'error' (str or None): Description of why the article was filtered out, if applicable.
            - 'articles_saved' (int): The number of articles saved (always 0 in this function).
            - 'unwanted_articles_saved' (int): The number of unwanted articles saved (0 or 1).
            - 'used_keywords' (List[str]): List of keywords found in the article (only if the article passes the filter).

    Details:
        This function performs the following steps:
        1. Retrieves keywords and blacklist keywords associated with the bot from the database.
        2. Checks if the article content contains any of the bot's keywords.
        3. Checks if the article content contains any of the bot's blacklist keywords.
        4. If the article doesn't match any keywords or contains blacklist keywords, it's saved as an unwanted article.
        5. If the article passes the filter, it saves the used keywords and returns the list.

    Raises:
        Exception: If an error occurs during database operations.
    """
    try:
        data_manager = DataManager()

        # Asegurarte de que article_content es una cadena (por si viene como lista de párrafos)
        if isinstance(article_content, list):
            article_content = " ".join(article_content)

        # Convertir el contenido a minúsculas una vez
        article_content_lower = article_content.lower()

        # Recuperar las palabras clave relacionadas con el bot desde la base de datos
        bot_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
        bot_keyword_names = [keyword.name.lower() for keyword in bot_keywords]  # Pasamos todo a minúsculas
        # Recuperar las palabras clave de la lista negra relacionadas con el bot
        bot_bl_keywords = Blacklist.query.filter_by(bot_id=bot_id).all()
        bot_bl_keyword_names = [bl_keyword.name.lower() for bl_keyword in bot_bl_keywords]  # Pasamos todo a minúsculas
        used_keywords = [keyword for keyword in bot_keyword_names if keyword in article_content_lower]

        used_blacklist_keywords = [bl_keyword for bl_keyword in bot_bl_keyword_names if bl_keyword in article_content_lower]

        if not used_keywords or used_blacklist_keywords:
            reason = ''
            if not used_keywords:
                print(f"[INFO] Article did not match any keywords, link: {news_link}")
                reason = 'Article did not match any keyword'
            elif used_blacklist_keywords:
                print(f"[INFO] Article contains blacklist keyword, link: {news_link}")
                reason = 'Article contains blacklist keyword'

            # Guardar el artículo como no deseado
            data_manager.save_unwanted_article(
                title=article_title,
                content=article_content,
                reason=reason,
                url=news_link,
                date=datetime.now(),
                bot_id=bot_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            return {
                'error': f"Article '{article_title}' filtered: {reason}",
                'articles_saved': 0,
                'unwanted_articles_saved': 1,
                'used_keywords': []
            }


        return {
            'error': None,
            'articles_saved': 0,
            'unwanted_articles_saved': 0,
            'used_keywords': used_keywords
        }

    except Exception as e:
        print(f"[ERROR] Exception occurred during keyword filtering: {str(e)}")
        raise