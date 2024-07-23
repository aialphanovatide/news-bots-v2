import os
from typing import List, Dict
from datetime import datetime
from playwright.sync_api import sync_playwright
from app.utils.helpers import resolve_redirects_playwright
from app.utils.analyze_links import fetch_article_content

def fetch_urls(url: str) -> Dict:
    print(f"\n[INFO] Starting URL fetch from: {url}")
    base_url = "https://news.google.com"
    result = {'success': False, 'data': [], 'errors': [], 'title': None}
    max_links = 10

    root_dir = os.path.abspath(os.path.dirname(__file__))
    user_data_dir = os.path.join(root_dir, 'tmp/playwright')

    os.makedirs(user_data_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(user_data_dir, headless=True, slow_mo=2000)
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("domcontentloaded", timeout=70000)

            news_links = []
            unique_urls = set()

            links = page.query_selector_all('a[href*="/articles/"]')
            for link in links:
                href = link.get_attribute('href').removeprefix('.')
                title = link.text_content().strip()

                if title:
                    full_link = base_url + href
                    if full_link not in unique_urls:
                        unique_urls.add(full_link)
                        news_links.append({'title': title, 'url': full_link})
                        
                    if len(news_links) >= max_links:
                        break

            result['data'] = news_links
            result['success'] = len(news_links) > 0

            browser.close()
            print(f"[INFO] URL fetch completed. Found {len(news_links)} unique links.")
            return result

    except Exception as e:
        error_message = f"[ERROR] Exception in fetch_urls: {str(e)}"
        print(error_message)
        result['errors'].append(error_message)
        return result

def fetch_news_links(url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int, category_slack_channel) -> dict:
    print(f'[INFO] Execution started for bot: {bot_name.upper()}')
    start_time = datetime.now()
    result = {'success': False, 'links_fetched': 0, 'errors': []}
    fetch_result = fetch_urls(url)

    if not fetch_result['success']:
        print(f"[ERROR] Failed to fetch URLs for bot: {bot_name.upper()}")
        return fetch_result

    news_links = fetch_result['data']
    print(f'[INFO] Number of links to scrape for {bot_name.upper()}: {len(news_links)}')
    result['links_fetched'] = len(news_links)

    for index, news_link in enumerate(news_links, 1):
        link_url = news_link['url']
        title = news_link['title']
        final_url = resolve_redirects_playwright(url=link_url)
        
        print(f'\n[INFO] Processing link {index}/{len(news_links)}')
        print(f'[INFO] Original URL: {link_url}')
        print(f'[INFO] Resolved URL: {final_url}')
        print(f'[INFO] Title: {title}')

        article_info = fetch_article_content(
            news_link=final_url,
            category_id=category_id,
            bot_id=bot_id,
            bot_name=bot_name,
            title=title,
            category_slack_channel=category_slack_channel
        )

        if 'error' in article_info:
            error_message = f"[ERROR] Failed to fetch content for {article_info['url']}, Reason: {article_info['error']}"
            print(error_message)
            result['errors'].append(error_message)
            continue
        
        if 'message' in article_info:
            print(f'[SUCCESS] {article_info["message"]}')
            continue
    
    result['success'] = len(result['errors']) == 0

    if result['success']:
        print(f'[INFO] Execution completed successfully for bot: {bot_name.upper()}')
    else:
        print(f'[WARNING] Execution completed with {len(result["errors"])} errors for bot: {bot_name.upper()}')
    
    end_time = datetime.now()
    execution_time = end_time - start_time
    print(f'[INFO] Total execution time: {execution_time}')
    return result

