import os
from typing import List, Dict
from datetime import datetime
from playwright.sync_api import sync_playwright
from app.utils.helpers import resolve_redirects_playwright
from app.utils.analyze_links import fetch_article_content


def fetch_urls(url: str) -> Dict:
    print("\nStarting fetching URLs...")
    base_url = "https://news.google.com"
    result = {'success': False, 'data': [], 'errors': [], 'title': None}
    max_links = 30

    root_dir = os.path.abspath(os.path.dirname(__file__))
    user_data_dir = os.path.join(root_dir, 'tmp/playwright')

    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(user_data_dir, headless=False, slow_mo=2000)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("domcontentloaded", timeout=70000)

            news_links = []
            unique_urls = set()

            # Extract links to news articles
            links = page.query_selector_all('a[href*="/articles/"]')

            for link in links:
                href = link.get_attribute('href').removeprefix('.')
                title = link.text_content().strip()

                # Verify title
                if title:
                    full_link = base_url + href
                    if full_link not in unique_urls:
                        unique_urls.add(full_link)
                        # Add the link and title to the list
                        news_links.append({'title': title, 'url': full_link})
                        
                    if len(news_links) >= max_links:
                        break

            result['data'] = news_links
            result['success'] = len(news_links) > 0

            browser.close()
            return result

    except Exception as e:
        print(f"Exception in fetch_urls: {str(e)}")
        return {'success': False, 'data': [], 'errors': [str(e)]}


def fetch_news_links(url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int, category_slack_channel) -> dict:
    
    print('--Execution started--')
    start_time = datetime.now()
    result = {'success': False, 'links_fetched': 0, 'errors': []}
    fetch_result = fetch_urls(url)

    if not fetch_result['success']:
        return fetch_result

    news_links = fetch_result['data']
  
    print(f'Length links to scrape for {str(bot_name).upper()}: ', len(news_links))
    result['links_fetched'] = len(news_links)

    # Fetch article, validate and save to DB
    for news_link in news_links:
        # Extract the URL from the news_link dictionary
        link_url = news_link['url']
        title = news_link['title']
        final_url = resolve_redirects_playwright(url=link_url)
        
        print('\n--- final_url ---', final_url)
        print('title: ', title)


        article_info = fetch_article_content(news_link=final_url,
                                             category_id=category_id,
                                             bot_id=bot_id,
                                             bot_name=bot_name,
                                             title=title,
                                             category_slack_channel=category_slack_channel)

        if 'error' in article_info:
            result['errors'].append(f"Error fetching content for {article_info['url']}, Reason: {article_info['error']}")
            continue
        
        if 'message' in article_info:
            print(f'\nSUCCEED: {article_info["message"]}')
            continue
    
    if len(result['errors']) == 0:
        result['success'] = True
        print('--- Execution ended ---')
    else:
        print(f'Length errors found during {str(bot_name).upper()} execution', result['errors'])
    
    end_time = datetime.now()
    
    print('\nTime consumed: ', start_time - end_time)
    return result


fetch_news_links(url='https://news.google.com/search?q=bitcoin%20btc%20%22bitcoin%20btc%22%20when%3A1d%20-buy%20-tradingview%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen',
                 bot_name='btc',
                 blacklist=[],
                 category_id=1,
                 bot_id=1,
                 category_slack_channel='C05RK7CCDEK'
                 )



# async def fetch_news_links(url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int) -> dict:
#     base_url = "https://news.google.com"
#     max_links = 30
#     result = {'success': False, 'links_fetched': 0, 'errors': []}

#     try:
#         async with async_playwright() as p:
#             browser = await p.chromium.launch(headless=True)
#             page = await browser.new_page()
#             await page.goto(url)
#             await page.wait_for_load_state("domcontentloaded", timeout=70000)
            
#             news_links = set()
            
#             # Extract links to news articles
#             links = await page.query_selector_all('a[href*="/articles/"]')
#             print('here')
#             for link in links:
#                 href = await link.get_attribute('href')
#                 title = await link.text_content()
                
#                 # Verify title
#                 if title and title.strip():
#                     full_link = base_url + href
                   
#                     try:
#                         resolved_link = resolve_redirects(full_link)
#                         if resolved_link:
#                             news_links.add(resolved_link)
#                     except Exception as e:
#                         # SEND MESSAGE TO SLACK
#                         result['errors'].append(f"Error resolving redirects for {full_link}: {str(e)}")
            
#             print(f'\nLength links to scrape for {str(bot_name).upper()}: ', len(news_links))
#             result['links_fetched'] = len(news_links)
            
#             # fetch article, validate and save to DB
#             for news_link in news_links:
#                 article_info = await fetch_article_content(news_link, category_id, title, bot_id, bot_name)
#                 if 'error' in article_info:
#                     # SEND MESSAGE TO SLACK
#                     result['errors'].append(f'\nError fetching content for {article_info['url']}, Reason: {article_info['error']}')
                
#                 if 'message' in article_info:
#                     print(f'\nSUCCEED: {article_info['message']}')
                
#                 if len(news_links) >= max_links:
#                     break
            
#             if len(result['errors']) == 0:
#                 result['success'] = True
#             else:
#                 print(f'Length errors found during {str(bot_name).upper()} execution', len(result['errors']))

#             return result

#     except Exception as e:
#         return {'success': False, 'links_fetched': 0, 'errors': [str(e)]}