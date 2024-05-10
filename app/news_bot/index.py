from typing import Optional, Dict, Union, List
# from app.helpers import save_list_to_json
# from app.filter_main_links import filter_links
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import asyncio
import aiohttp

# --------
import re
import aiofiles
import json
import os

# Saves a list of elements into a JSON file
async def save_list_to_json(data_list, filename='data.json'):
    try:
        if os.path.exists(filename):
            count = 1
            while True:
                new_filename = f"{os.path.splitext(filename)[0]}_{count}.json"
                if not os.path.exists(new_filename):
                    break
                count += 1
            filename = new_filename

        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data_list, ensure_ascii=False, indent=4))
        print("Data saved to", filename)
    except Exception as e:
        print("Error:", e)



# this function filter links retrieves from the main URL
async def filter_links(urls: List[str], prefix: str, exclude_terms: List[str] = ['privacy-policy', 'glossary', 'careers', 'about', 'newsletter', '/events/', 
                                               'discord.com', 'tiktok.com', 'b1.com', 'youtube.com',
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


# Topic: Velo, velodrome, crypto - TABLE BOT
# link_keywords: Velo, velodrome =  Words to search to inlcude in the search url - NEW TABLE TO CREATE
# link_blacklist: msn = Words to exclude in the search url - NEW TABLE TO CREATE


# Possible improvements: google news search by date and intext:[list of keywords]
async def fetch_news_links(blacklist: list[str], keywords: list[str], topic: list[str], url: Optional[str] = None) -> Dict[str, Union[str, List[str]]]:
    """
    Fetches news related to the given topic asynchronously.

    Args:
        topic (str): The topic to search for.
        url (str, optional): The URL to fetch news from. Defaults to None.
        prefix (str, optional): The prefix to be added to URLs if necessary. Defaults to 'https://news.google.com/'.

    Returns:
        Dict[str, Union[str, List[str]]]: A dictionary containing either the fetched news (if successful) or an error message.
            - 'error' (str): An error message if an error occurred, otherwise None.
            - 'response' (List[str]): A list of URLs containing the fetched news, or None if an error occurred or no news was found.
    """
    response = {'error': None, 'response': None}
    
    try:
        if not topic or not isinstance(topic, str):
            raise ValueError('topic is required and must be a string')
        
        if url and not isinstance(url, str):
            raise ValueError('url is required and must be a string')
        
        
        search_url = f'https://news.google.com/search?q={topic}&hl=en-US&gl=US&ceid=US%3Aen' if not url else url
        parsed_url = urlparse(search_url)
        # print('parsed_url: ', parsed_url)
        prefix = f"{parsed_url.scheme}://{parsed_url.netloc}"

        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response_data:
                if response_data.status == 200:
                    soup = BeautifulSoup(await response_data.text(), 'html.parser')
                    links = soup.find_all('a')
                    news = [link.get('href') for link in links if links]
                  

                    filtered_news = await filter_links(urls=news, prefix=prefix)
                    await save_list_to_json(data_list=filtered_news, filename=f'{parsed_url.netloc}.json')
                        
                    if 'error' in filtered_news:
                        response['error'] = filtered_news['error']
                    else:
                        response['response'] = filtered_news['response']
                else:
                    response['error'] = f"Failed to fetch news: {await response_data.text()}"

    except asyncio.TimeoutError:
        response['error'] = "Failed to fetch news: Timeout error."
    except aiohttp.ClientError as e:
        response['error'] = f"Failed to fetch news: {str(e)}."
    except ValueError as e:
        response['error'] = f'Value error: {str(e)}'
    except Exception as e:
        response['error'] = f"An unexpected error occurred: {str(e)}."

    return response





# Example usage:
async def main():
    topic = "gold"
    url = "https://cointelegraph.com/tags/bitcoin"

    print(await fetch_news_links(topic=topic, url=url))


    # google news
    # await fetch_news_links(topic=topic)


# Run the main function
asyncio.run(main())