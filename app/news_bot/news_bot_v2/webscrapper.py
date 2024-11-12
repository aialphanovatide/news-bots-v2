import os
import json
import requests
import random
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse


class WebScraper:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.headers = self._get_headers()
       
    def logger(self, message: str):
        if self.verbose:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] - {message}")

    def _get_headers(self) -> dict:
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',  #Do Not Track Request Header
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
    def scrape_rss(self, url: str) -> List[Dict[str, str]]:
        try:
            # Log the start of RSS feed scraping
            self.logger(f"Scraping RSS feed: {url}")

            # Validate if URL is RSS feed
            if 'rss' not in url:
                raise ValueError("Provided URL is not a valid RSS feed")
            
            # Parse the RSS feed using feedparser
            feed = feedparser.parse(url)
            
            # Log successful parsing and number of entries
            self.logger(f"Feed parsed successfully")
            self.logger(f"Number of entries: {len(feed.entries)}")
            
            # Extract links and published dates from entries
            items = []
            for entry in feed.entries:
                item = {
                    'link': entry.get('link', ''),
                    'published': entry.get('published', '')
                }
                if item['link']:  # Only add items with a valid link
                    items.append(item)
            
            # Log first few entries (optional for debugging)
            if feed.entries and self.verbose:
                self.logger("First 5 entries (if available):")
                for entry in feed.entries[:5]:
                    self.logger(f"Title: {entry.get('title', 'N/A')}")
                    self.logger(f"Link: {entry.get('link', 'N/A')}")
                    self.logger(f"Published: {entry.get('published', 'N/A')}")
                    self.logger("---")
            
            # Log the scraped items
            self.logger(f"Scraped items: {items}")
            
            return items
        except Exception as e:
            raise Exception(f"Error scraping RSS feed: {e}")



# def main():
#     url_1 = 'https://vitalik.eth.limo/'
#     url_2 = "https://news.google.com/rss/search?q=crypto+when:1d&hl=en-US&gl=US&ceid=US:en"
#     url_3 = 'https://news.google.com/search?q=ethereum%20%22ethereum%22%20when%3A1d%20-msn%20-buy%20-yahoo&hl=en-US&gl=US&ceid=US%3Aen'
#     url_4 = 'https://news.google.com/rss/search?q=bitcoin+btc+%22bitcoin+btc%22+when:1d+-buy+-tradingview+-msn+-medium+-yahoo&hl=en-US&gl=US&ceid=US:en'
#     url_5 = 'https://www.bloomberg.com/markets/stocks'
#     url_6 = 'https://news.google.com/rss/search?q=FTM%20Fantom%20%22FTM%22%20%22Fantom%22%20when%3A1d%20-msn%20-medium%20-buy%20-yahoo&hl=en-US&gl=US&ceid=US%3Aen'

#     scraper = WebScraper(url_6, verbose=True, save_to_file=None, save_format='none')  #Enable verbose mode for debugging
#     scraper.scrape()

# if __name__ == "__main__":
#     main()