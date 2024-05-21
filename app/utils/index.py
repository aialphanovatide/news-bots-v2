from typing import List, Dict
from app.utils.helpers import resolve_redirects
from playwright.async_api import async_playwright
from app.utils.analyze_links import fetch_article_content



# Get all urls from a source
async def fetch_urls(url: str) -> Dict:
    base_url = "https://news.google.com"
    result = {'success': False, 'data': [], 'errors': [], 'title': None}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=20)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded", timeout=70000)
            
            news_links = set()
            
            # Extract links to news articles
            links = await page.query_selector_all('a[href*="/articles/"]')
            for link in links:
                href = await link.get_attribute('href')
                title = await link.text_content()
                
                # Verify title
                if title and title.strip():
                    full_link = base_url + href
                    result['title'] = title
                    try:
                        resolved_link = resolve_redirects(full_link)
                        if resolved_link:
                            news_links.add(resolved_link)
                    except Exception as e:
                        result['errors'].append(f"Error resolving redirects for {full_link}: {str(e)}")
            
            result['data'] = list(news_links)
            result['success'] = True if len(news_links) > 0 else False
            return result

    except Exception as e:
        return {'success': False, 'data': [], 'errors': [str(e)]}


# Process URLs, validate, save to DB and send notififcations
async def fetch_news_links(url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int) -> dict:
    max_links = 30
    result = {'success': False, 'links_fetched': 0, 'errors': []}

    fetch_result = await fetch_urls(url)
    
    if not fetch_result['success']:
        return fetch_result

    news_links = fetch_result['data']
    title = fetch_result['title']
    print(f'Length links to scrape for {str(bot_name).upper()}: ', len(news_links))
    result['links_fetched'] = len(news_links)
    
    
    # Fetch article, validate and save to DB
    for news_link in news_links:
        article_info = await fetch_article_content(news_link=news_link,
                                                   category_id=category_id,
                                                    bot_id=bot_id,
                                                    bot_name=bot_name,
                                                    title=title)
        if 'error' in article_info:
            result['errors'].append(f"Error fetching content for {article_info['url']}, Reason: {article_info['error']}")
        
        if 'message' in article_info:
            print(f'SUCCEED: {article_info["message"]}')
        
        if len(news_links) >= max_links:
            break
    
    if len(result['errors']) == 0:
        result['success'] = True
    else:
        print(f'Length errors found during {str(bot_name).upper()} execution', len(result['errors']))

    return result




















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