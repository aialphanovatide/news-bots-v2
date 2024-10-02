from datetime import datetime
from typing import Any, Dict, List
import re
from app.utils.similarity import cosine_similarity_with_openai_classification
from config import Article, Session, UnwantedArticle
from app.news_bot.webscrapper.data_manager import DataManager

data_manager=DataManager()


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


def content_filter(content, blacklist, keywords):
    # Implement content filtering logic
    pass




