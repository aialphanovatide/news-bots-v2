from typing import List
from app.utils.helpers import resolve_redirects
from playwright.async_api import async_playwright
from app.utils.analyze_links import fetch_article_content


async def fetch_news_links(url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int) -> dict:
    base_url = "https://news.google.com"
    max_links = 30
    result = {'success': False, 'links_fetched': 0, 'errors': []}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(slow_mo=30, headless=False)
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
                   
                    try:
                        resolved_link = resolve_redirects(full_link)
                        if resolved_link:
                            news_links.add(resolved_link)
                    except Exception as e:
                        # SEND MESSAGE TO SLACK
                        result['errors'].append(f"Error resolving redirects for {full_link}: {str(e)}")
            
            print(f'\nLength links to scrape for {str(bot_name).upper()}: ', len(news_links))
            result['links_fetched'] = len(news_links)
            
            # fetch article, validate and save to DB
            for news_link in news_links:
                article_info = await fetch_article_content(news_link, category_id, title, bot_id, bot_name)
                if 'error' in article_info:
                    # SEND MESSAGE TO SLACK
                    result['errors'].append(f'\nError fetching content for {article_info['url']}, Reason: {article_info['error']}')
                
                if 'message' in article_info:
                    print(f'\nSUCCEED: {article_info['message']}')
                
                if len(news_links) >= max_links:
                    break
            
            if len(result['errors']) == 0:
                result['success'] = True
            else:
                print(f'Length errors found during {str(bot_name).upper()} execution', len(result['errors']))

            return result

    except Exception as e:
        return {'success': False, 'links_fetched': 0, 'errors': [str(e)]}




