import requests
from bs4 import BeautifulSoup
import re

def request_to_link(link):
   """
   Request to a link and return the article text content.
   Supports various news article formats and common HTML structures.
   
   Args:
       link (str): URL to request
       
   Returns:
       str: Article text content
       
   Raises:
       requests.exceptions.RequestException: If request fails
       ValueError: If no article content could be extracted
   """
   try:
       headers = {
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
           'Accept-Language': 'en-US,en;q=0.5',
           'Connection': 'keep-alive',
       }
       
       response = requests.get(link, headers=headers, timeout=10)
       response.raise_for_status()
       soup = BeautifulSoup(response.text, 'html.parser')
       
       # Remove unwanted elements
       for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
           element.decompose()
       
       # Common article content selectors
       article_selectors = [
           {'class': 'caas-body'},              # Yahoo
           {'class': 'article-body'},           # Common pattern
           {'class': 'post-content'},           # Common pattern
           {'class': 'entry-content'},          # WordPress
           {'class': 'content-body'},           # Common pattern
           {'itemprop': 'articleBody'},         # Schema.org
           {'class': 'story-body'},             # BBC
           {'class': 'article__body'},          # Various news sites
           {'role': 'article'},                 # ARIA role
       ]
       
       # Try to find article content using different selectors
       article_text = ""
       for selector in article_selectors:
           article_body = soup.find(['article', 'div', 'main'], selector)
           if article_body:
               # Get all text paragraphs
               paragraphs = article_body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
               if paragraphs:
                   article_text = ' '.join([p.get_text().strip() for p in paragraphs])
                   break
       
       # Fallback: If no content found, try getting main content area
       if not article_text:
           main_content = soup.find('main') or soup.find('article')
           if main_content:
               paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
               article_text = ' '.join([p.get_text().strip() for p in paragraphs])
       
       # Clean up the text
       article_text = ' '.join(article_text.split())  # Remove extra whitespace
       article_text = re.sub(r'\s+([.,!?])', r'\1', article_text)  # Fix punctuation spacing
       
       if not article_text:
           raise ValueError("No article content could be extracted from the URL")
           
       return article_text
       
   except requests.exceptions.RequestException as e:
       raise requests.exceptions.RequestException(f"Failed to fetch URL: {str(e)}")
   except Exception as e:
       raise ValueError(f"Error processing article content: {str(e)}")