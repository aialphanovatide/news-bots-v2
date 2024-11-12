import re
import pytz
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from config import Article, Blacklist, Keyword, UnwantedArticle
from app.utils.similarity import cosine_similarity_with_openai_classification

def is_recent_date(date_str: str, max_age_hours: int = 24) -> bool:
    """
    Validate if the given date string is recent within specified hours
    
    Args:
        date_str: Date string in format like 'Tue, 12 Nov 2024 12:01:45 GMT'
        max_age_hours: Maximum age in hours for a date to be considered recent
        
    Returns:
        bool: True if date is within max_age_hours, False otherwise
    """
    try:
        # Parse the date string
        article_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        
        # Convert to UTC timezone
        utc = pytz.UTC
        article_date = utc.localize(article_date)
        current_time = datetime.now(utc)
        
        # Calculate time difference
        time_diff = current_time - article_date
        
        # Check if within max age
        return abs(time_diff) <= timedelta(hours=max_age_hours)
        
    except Exception as e:
        raise Exception(f"Date validation failed: {str(e)}")



def is_content_similar(
    content: str,
    bot_id: int,
    limit: int = 10,
    threshold: float = 0.9,
) -> Tuple[bool, Optional[float]]:
    """
    Check if article content is similar to recently saved articles.

    Compares the given content against the most recent articles for a specific bot
    using OpenAI's cosine similarity. If similarity exceeds the threshold, the article
    is saved as unwanted.

    Args:
        content (str): The article content to check
        bot_id (int): ID of the bot performing the check
        title (str): Title of the article being checked
        url (str): URL of the article being checked
        limit (int, optional): Number of recent articles to check against. Defaults to 10
        threshold (float, optional): Similarity threshold (0.0 to 1.0). Defaults to 0.9

    Returns:
        Tuple[bool, Optional[float]]: A tuple containing:
            - bool: True if similar content found, False otherwise
            - float: Similarity score if found, None otherwise

    Raises:
        BadRequest: If input parameters are invalid
        InternalServerError: If there's an error during similarity checking
    """
    try:
        # Input validation
        if not isinstance(content, str) or not content.strip():
            raise Exception("Content must be a non-empty string")
        if not isinstance(bot_id, int) or bot_id <= 0:
            raise Exception("bot_id must be a positive integer")
        
        # Convert list content to string if necessary
        if isinstance(content, list):
            content = " ".join(content)

        # Get recent articles
        recent_articles = Article.query.filter_by(bot_id=bot_id)\
                                    .order_by(Article.date.desc())\
                                    .limit(limit)\
                                    .all()

        # Check similarity against each article
        for article in recent_articles:
            try:
                similarity_score = cosine_similarity_with_openai_classification(
                    article.content, 
                    content
                )
                
                if similarity_score and similarity_score >= threshold:
                    return True, similarity_score
                    
            except Exception as e:
                raise Exception(
                    f"Error calculating similarity: {str(e)}"
                )

        return False, None

    except Exception as e:
        raise Exception(f"Content similarity check failed: {str(e)}")


def is_url_analyzed(url: str, bot_id: int) -> bool:
    """
    Check if a URL has been previously processed by a specific bot.

    Verifies if the given URL exists in either the Article or UnwantedArticle tables
    for the specified bot. This prevents duplicate processing of articles and ensures
    each URL is only analyzed once per bot. The check is case-insensitive.

    Args:
        url (str): The URL to check for previous analysis
        bot_id (int): The ID of the bot to check against

    Returns:
        bool: True if the URL has been previously analyzed by this bot,
              False if the URL is new and hasn't been processed

    Example:
        >>> is_url_analyzed("https://example.com/article", 123)  # Returns same result for:
        >>> is_url_analyzed("HTTPS://EXAMPLE.COM/ARTICLE", 123)  # These are treated as identical
    """
    # Convert URL to lowercase for case-insensitive comparison
    url_lower = url.lower()
    
    # Check if URL has been analyzed before using case-insensitive comparison
    existing_unwanted_article = UnwantedArticle.query.filter(
        UnwantedArticle.bot_id == bot_id,
        UnwantedArticle.url.ilike(url_lower)
    ).first()
    
    existing_article = Article.query.filter(
        Article.bot_id == bot_id,
        Article.url.ilike(url_lower)
    ).first()
    
    return bool(existing_unwanted_article or existing_article)


def filter_link(url: str, exclude_terms: List[str] = [
    'privacy-policy', 'glossary', 'careers', 'about', 'newsletter', 'events',
    'discord.com', 'tiktok.com', 'b1.com', 'youtube.com', 'yahoo.com', 'uk.movies.yahoo.com',
    'advertise', 'contact-us', 'cookie-policy', 'terms-of-service', 'sirwin', 'bs3', 'tag', 'learn'
]) -> str:
    """
    Filter a URL based on exclude terms and social media patterns.

    Args:
        url (str): The URL to filter.
        exclude_terms (List[str]): A list of terms to exclude from the URL.

    Returns:
        str: The original URL if it passes the filter, None otherwise.

    Raises:
        ValueError: If the input URL is invalid or if the exclude_terms list is empty.
        Exception: For any unexpected errors during processing.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Invalid input. Please provide a non-empty URL string.")
    
    if not isinstance(exclude_terms, list) or not exclude_terms:
        raise ValueError("Invalid input. Please provide a non-empty list of exclude terms.")

    try:
        # Normalize URL
        normalized_url = url.lower().strip()

        # Compile regex patterns
        exclude_pattern = re.compile(r'|'.join(map(re.escape, exclude_terms)))
        social_media_pattern = re.compile(r'(facebook\.com|twitter\.com|linkedin\.com|instagram\.com|sponsored|t\.me)')

        # Check if URL passes all filters
        if not exclude_pattern.search(normalized_url) and not social_media_pattern.search(normalized_url):
            return url
        else:
            return None

    except Exception as e:
        raise Exception(f"Error processing URL: {str(e)}") from e
    

def check_article_keywords(
    content: str,
    bot_id: int,
) -> Tuple[List[str], List[str]]:
    """
    Check if article content matches bot's keywords or blacklist terms.

    Args:
        content (str): Article content to analyze
        bot_id (int): ID of the bot performing the check

    Returns:
        Tuple[List[str], List[str]]: (matching_keywords, matching_blacklist)
        - If keywords match: ([keywords], [])
        - If blacklist matches: ([], [blacklist_terms])
        - If no matches: ([], [])

    Raises:
        ValueError: For invalid input parameters
        DatabaseError: For database operation failures
        Exception: For unexpected errors
    """
    # Input validation
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Content must be a non-empty string")
    if not isinstance(bot_id, int) or bot_id <= 0:
        raise ValueError("bot_id must be a positive integer")

    # Normalize content
    normalized_content = " ".join(content) if isinstance(content, list) else content
    normalized_content = normalized_content.lower().strip()

    try:
        # Get keywords and blacklist
        keywords = Keyword.query.with_entities(
            func.lower(Keyword.name)
        ).filter_by(bot_id=bot_id).all()
        
        blacklist = Blacklist.query.with_entities(
            func.lower(Blacklist.name)
        ).filter_by(bot_id=bot_id).all()
    except Exception as e:
        raise Exception(f"Failed to fetch keywords/blacklist: {str(e)}")

    # Process matches
    keyword_list = [k[0] for k in keywords]
    blacklist_list = [b[0] for b in blacklist]

    matching_keywords = [kw for kw in keyword_list if kw in normalized_content]
    matching_blacklist = [bl for bl in blacklist_list if bl in normalized_content]

    # Return matches based on priority (blacklist takes precedence)
    if matching_blacklist:
        return [], matching_blacklist
    if matching_keywords:
        return matching_keywords, []
    return [], []