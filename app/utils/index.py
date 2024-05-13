from playwright.async_api import async_playwright
from typing import List, Dict, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.utils.helpers import resolve_redirects
from app.utils.analyze_links import fetch_url
import requests
import re


def filter_links(urls: List[str], prefix: str, exclude_terms: List[str] = ['privacy-policy', 'glossary', 'careers', 'about', 'newsletter', '/events/', 
                                               'discord.com', 'tiktok.com', 'b1.com', 'youtube.com', 'medium.com', 'msn.com', 'msn', 
                                               'advertise', 'contact-us', 'cookie-policy', 'terms-of-service', 'sirwin', 'bs3', '/tag/','/learn/']) -> dict:
    try:
        filtered_urls = []
        social_media_regex = r'(facebook\.com|twitter\.com|linkedin\.com|instagram\.com|sponsored)'
        telegram_regex = r't\.me'
        
        for url in urls:
            if url is not None and url.strip() != '' and \
               not any(term in url for term in exclude_terms) and \
               not re.search(social_media_regex, url) and \
               not re.search(telegram_regex, url):
                if prefix.startswith("https://news.google.com"):
                    if url.startswith('./article'):
                        url = prefix + url[1:]
                        filtered_urls.append(url)
                else:
                    if len(url) > 20:
                        url = prefix + url
                        filtered_urls.append(url)
        
        return {'response': filtered_urls}
    except Exception as e:
        return {'error': str(e)}
    


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

