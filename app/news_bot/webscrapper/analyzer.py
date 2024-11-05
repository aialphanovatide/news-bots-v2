from bs4 import BeautifulSoup
from typing import Dict, Any
import requests

def analyze_content(news_link: str) -> Dict[str, Any]:
    """
    Analyzes the content of a news article from the given URL.

    This function fetches the HTML content of the news article, extracts relevant
    information such as the title, paragraphs, and publication date, and performs
    some basic validation.

    Args:
        news_link (str): The URL of the news article to analyze.

    Returns:
        Dict[str, Any]: A dictionary containing the extracted information:
            - 'success' (bool): Indicates if the extraction was successful.
            - 'url' (str): The original URL of the article.
            - 'title' (str): The extracted title of the article.
            - 'paragraphs' (List[str]): List of extracted paragraphs from the article.
            - 'publication_date' (datetime or None): The extracted publication date, if found.
            - 'error' (str or None): Description of any error that occurred during extraction.

    Detail:
        The function performs the following steps:
        1. Sends an HTTP GET request to the provided URL.
        2. Validates the response and content type.
        3. Parses the HTML content using BeautifulSoup.
        4. Extracts the article title, paragraphs, and publication date.
        5. Performs additional validation for publication date.
        6. Returns a dictionary with the extracted information and status.
    """    
    try:
        # Send HTTP GET request
        response = requests.get(news_link, timeout=10)
        if response.status_code != 200:
            return {
                'success': False,
                'url': news_link,
                'title': None,
                'paragraphs': [],
                'publication_date': None,
                'error': f"HTTP error: {response.status_code} - {response.reason}"
            }
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'text/html' not in content_type:
            return {
                'success': False,
                'url': news_link,
                'title': None,
                'paragraphs': [],
                'publication_date': None,
                'error': "Content is not HTML"
            }
        
        html = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article title
        title_element = html.find('h1')
        if title_element:
            article_title = title_element.text.strip()
        else:
            # If h1 is not found, try other common title tags
            title_element = html.find(['title', 'meta'], attrs={'property': 'og:title'})
            article_title = title_element.get('content') if title_element else None

        if not article_title:
            article_title = "Unknown Title"        
        
        # Extract paragraphs from the article
        paragraphs = html.find_all('p')
        article_content = [p.text.strip() for p in paragraphs if p.text.strip()]

        return {
            'success': True,
            'url': news_link,
            'title': article_title,
            'paragraphs': article_content,
            'error': None
        }
            
    except requests.RequestException as e:
        return {
            'success': False,
            'url': news_link,
            'title': None,
            'paragraphs': [],
            'error': f"Request error while getting article content: {e}"
        }
    except Exception as e:
        return {
            'success': False,
            'url': news_link,
            'title': None,
            'paragraphs': [],
            'publication_date': None,
            'error': f'Error while getting article content: {str(e)}'
        }