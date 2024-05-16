from playwright.async_api import async_playwright
from typing import List, Dict, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.utils.helpers import resolve_redirects
from app.utils.analyze_links import fetch_url


async def fetch_news_links(url: str, keywords: List[str], blacklist: List[str], category_id: int, bot_id: int) -> None:
    base_url = "https://news.google.com"
    max_links = 30
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(slow_mo=10, headless=False)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded", timeout=70000)
            
            news_links = set()
            news_content = []
            for link in await page.query_selector_all('a[href*="/articles/"]'):
                href = await link.get_attribute('href')
                title = await link.text_content()
                # Verificar si el título no está vacío antes de agregar el enlace
                if title.strip() and not any(href.startswith(domain) for domain in blacklist):
                    full_link = base_url + href
                    resolved_link = resolve_redirects(full_link)
                    if resolved_link:
                        news_links.add(resolved_link)
            for news_link in news_links:
                await fetch_url(news_link, category_id,title, bot_id)
                if len(news_content) >= max_links:
                    break

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

