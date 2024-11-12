import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from requests.exceptions import RequestException
from werkzeug.exceptions import HTTPException


class ArticleExtractor:
    """
    This class is designed to extract content from news articles. 

    1. Fetches the HTML content of the article using the provided URL.
    2. Parses the fetched HTML.
    3. Extracts the article title and content based on common HTML structures found in news articles. This includes identifying and extracting the title from HTML tags such as `<title>` or `<h1>`, and the content from tags like `<p>` or `<div>`.

    The extracted content is then returned as a dictionary, providing a structured representation of the article's metadata and content. 
    """
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    TIMEOUT = 10
    
    @staticmethod
    def extract_article_content(url: str) -> Dict[str, Any]:
        """
        Extracts content from a news article URL.

        Args:
            url (str): The URL of the news article

        Returns:
            Dict[str, Any]: Extracted article data containing:
                - title (str): Article title
                - content (list): Article paragraphs
                - url (str): Original URL

        Raises:
            Exception: For any errors during content extraction
        """
        try:
            # Validate input
            if not url or not isinstance(url, str):
                raise ValueError("Invalid URL provided")

            # Fetch content
            response = requests.get(
                url,
                headers=ArticleExtractor.HEADERS,
                timeout=ArticleExtractor.TIMEOUT
            )
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                raise Exception(f"Invalid content type: {content_type}")

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = ArticleExtractor._extract_title(soup)
            
            # Extract content
            content = ArticleExtractor._extract_article_text(soup)
            
            if not content:
                raise Exception("No content found in article")

            return {
                'title': title,
                'content': content[0],
                'url': url
            }

        except RequestException as e:
            raise Exception(f"Failed to fetch article: {str(e)}")
        except ValueError as e:
            raise Exception(str(e))
        except Exception as e:
            raise Exception(f"Content extraction failed: {str(e)}")

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """Extract article title from HTML."""
        # Try multiple title sources in order of preference
        title_selectors = [
            ('h1', None),
            ('meta[property="og:title"]', 'content'),
            ('title', None)
        ]

        for selector, attr in title_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get(attr) if attr else element.text.strip()

        return "Unknown Title"

    @staticmethod
    def _extract_content(soup: BeautifulSoup) -> list:
        """Extract article content from HTML."""
        # Find all paragraphs
        paragraphs = soup.find_all('p')
        
        # Clean and filter paragraphs
        content = [
            p.text.strip() 
            for p in paragraphs 
            if p.text.strip() and len(p.text.strip()) > 30  # Avoid short snippets
        ]

        return content
    
    @staticmethod
    def _extract_article_text(html_content: BeautifulSoup) -> list:
        """
        Extract article text content from HTML, considering multiple content elements
        while filtering out non-article content.

        Args:
            html_content (BeautifulSoup): Parsed HTML content

        Returns:
            list: List of relevant text content from the article
        """
        # Common article container classes/IDs
        article_containers = [
            'article',
            'main-content',
            'article-content',
            'story-content',
            'post-content',
            'entry-content'
        ]

        # Find main article container
        main_container = None
        for container in article_containers:
            main_container = (
                html_content.find('article') or
                html_content.find(class_=container) or
                html_content.find(id=container)
            )
            if main_container:
                break
        
        # If no container found, use body
        content_area = main_container or html_content.find('body')

        # Relevant content tags
        content_elements = content_area.find_all([
            'p',        # Regular paragraphs
            'h2',       # Subheadings
            'h3',       # Sub-subheadings
            'li',       # List items
            'blockquote'# Quotes
        ])

        # Unwanted content indicators
        unwanted_classes = {
            'nav', 'menu', 'header', 'footer', 'sidebar',
            'comment', 'advertisement', 'social', 'related',
            'share', 'newsletter', 'subscription'
        }

        unwanted_text_patterns = {
            'cookie', 'privacy policy', 'terms of service',
            'subscribe', 'sign up', 'newsletter', 'advertisement',
            'sponsored', 'recommended', 'popular', 'trending',
            'follow us', 'share this', 'comments'
        }

        article_content = []
        
        for element in content_elements:
            # Skip elements with unwanted classes
            element_classes = {cls.lower() for cls in element.get('class', [])}
            if element_classes & unwanted_classes:
                continue

            # Get and clean text
            text = element.get_text().strip()
            
            # Skip if text is too short or contains unwanted patterns
            if (
                len(text) < 30 or
                any(pattern in text.lower() for pattern in unwanted_text_patterns)
            ):
                continue

            # Add text with its HTML tag for context
            tag_name = element.name
            if tag_name in ['h2', 'h3']:
                # Add subheadings with some distinction
                article_content.append(f"[{tag_name.upper()}] {text}")
            else:
                article_content.append(text)

        return article_content


# Example of usage:
# if __name__ == "__main__":
#     content = ArticleExtractor.extract_article_content("https://www.entrepreneur.com/en-in/news-and-trends/algorand-foundation-partners-with-t-hub-to-empower/482683")
#     print(content)
