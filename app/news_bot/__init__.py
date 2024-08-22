print("Initializing News Bot")

# Set package-level variables
__version__ = "1.0.0"
__author__ = "AI ALPHA"

# Import key components to make them available at the package level
from config import db
from .grok import parse_grok_response, fetch_grok_news
from .s3 import generate_and_upload_image
from .validators import validate_keywords, is_url_article_already_analyzed, validate_blacklist_keywords, validate_article_similarity
from .db import validate_and_save_article_data

# Define what gets imported with a wildcard import (eg: from news_bots import *)
__all__ = [ 'db','parse_grok_response', 'fetch_grok_news', 'generate_and_upload_image', 'validate_keywords', 'is_url_article_already_analyzed', 'validate_blacklist_keywords', 'validate_article_similarity', 'validate_and_save_article_data']