from typing import List
import re

# this function filter links retrieves from the main URL
async def filter_links(urls: List[str], prefix: str, exclude_terms: List[str] = ['privacy-policy', 'glossary', 'careers', 'about', 'newsletter', '/events/', 
                                               'discord.com', 'tiktok.com', 'b1.com', 'youtube.com','yahoo.com',
                                               'advertise', 'contact-us', 'cookie-policy', 'terms-of-service', 'sirwin', 'bs3', '/tag/','/learn/']) -> dict:
    
    try:
        # Check if input is valid
        if not isinstance(urls, list) or not urls:
            raise ValueError("Invalid input. Please provide a non-empty list of urls") 
        
        if not prefix or not isinstance(prefix, str):
            raise ValueError("Invalid input. Please provide a valid prefix") 

        if not exclude_terms or not isinstance(exclude_terms, list):
            raise ValueError("Invalid input. Please provide a non-empty list of exclude terms")
        
        filtered_urls = []
        social_media_regex = r'(facebook\.com|twitter\.com|linkedin\.com|instagram\.com|sponsored)'
        telegram_regex = r't\.me'
        
        for url in urls:
            # general filters
            if url is not None and url.strip() != '' and \
               not any(term in url for term in exclude_terms) and \
               not re.search(social_media_regex, url) and \
               not re.search(telegram_regex, url):
                # filter for when it's a google news url
                if prefix.startswith("https://news.google.com"):
                    if url.startswith('./article'):
                        url = prefix + url[1:]
                        filtered_urls.append(url)
                else:
                    if len(url) > 20:
                        url = prefix + url
                        filtered_urls.append(url)
        
        return {'response': filtered_urls}
    except ValueError as e:
        return {'error': f'Value error: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}