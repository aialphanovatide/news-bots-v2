import asyncio
from datetime import datetime
import logging
from typing import List
from app.news_bot.grok import fetch_grok_news
from app.news_bot.webscrapper.index import WebScrapper
from app.utils.helpers import resolve_redirects_playwright
from config import db
from app.news_bot.validators import (
    validate_keywords,
    is_url_article_already_analyzed,
    validate_blacklist_keywords,
    validate_article_similarity
)
from app.news_bot.db import validate_and_save_article_data
from app.news_bot.s3 import generate_and_upload_image

class NewsBot:
    def __init__(self, bot_id: int, bot_name: str, db_session, verbose: bool = True):
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.db_session = db_session
        self.verbose = verbose
        
        # Initialize current article details
        self.current_article_title = None
        self.current_raw_article_content = None
        self.current_news_link = None
        self.current_used_keywords = []
        
        # Setup logger
        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger(f"NewsBot-{self.bot_name}")
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def is_url_article_already_analyzed(self, url: str) -> bool:
        return is_url_article_already_analyzed(self=self, url=url)


    def validate_article_similarity(self, content: str, url: str, bot_id: int) -> dict:
        return validate_article_similarity(self, content, url, bot_id)

    def validate_keywords(self, content: str, title: str) -> dict:
        return validate_keywords(self, content, title)

    def validate_blacklist_keywords(self, content: str, title: str) -> dict:
        return validate_blacklist_keywords(self, content, title)

    def validate_and_save_article_data(self, title: str, summary: str, image_filename: str, url: str, used_keywords: str) -> dict:
        return validate_and_save_article_data(self, title, summary, image_filename, url, used_keywords)
    
    def generate_and_upload_image(news_bot, content: str,) -> dict:
        return generate_and_upload_image(news_bot=news_bot, content=content)
    
    def fetch_news_links(self, url: str, bot_name: str, blacklist: List[str], category_id: int, bot_id: int, category_slack_channel) -> dict:
        print('[INFO] Execution started for bot: ', bot_name.upper())
        start_time = datetime.now()
        result = {'success': False, 'links_fetched': 0, 'errors': []}
        fetch_result = WebScrapper.fetch_urls(self, url=url)
        if not fetch_result['success']:
            self.logger.error('Failed to fetch URLs for bot: ', bot_name.upper())
            return fetch_result

        news_links = fetch_result['data']
        print(f'[INFO] Number of links to scrape for {bot_name.upper()}: {len(news_links)}')
        result['links_fetched'] = len(news_links)

        for index, news_link in enumerate(news_links, 1):
            link_url = news_link['url']
            title = news_link['title']
            
            # Debugging para asegurarse de que el título es válido
            if not title:
                self.logger.error(f"[ERROR] No se pudo extraer el título para el link: {link_url}")
                continue

            final_url = resolve_redirects_playwright(url=link_url)
            print(f'[INFO] Processing link {index}/{len(news_links)}')

            # Set the current article details
            self.current_article_title = title
            self.current_news_link = final_url
            # Ahora deberías llamar a `generate_and_upload_image` con la seguridad de que `self.current_article_title` está configurado
            article_info = WebScrapper.fetch_article_content(
                newsbot=self,
                news_link=final_url,
                category_id=category_id,
                bot_id=bot_id,
                bot_name=bot_name,
                title=title,
                category_slack_channel=category_slack_channel
            )
            
            if 'error' in article_info:
                error_message = f"Failed to fetch content for {article_info['url']}, Reason: {article_info['error']}"
                self.logger.error(error_message)
                result['errors'].append(error_message)
                continue
            
            if 'message' in article_info:
                print(f"[INFO] : {article_info['message']}")
                continue


        result['success'] = len(result['errors']) == 0

        if result['success']:
            print('[INFO] Execution completed successfully for bot: ', bot_name.upper())
        else:
            print('[ERROR] ERROR Execution for bot: ', bot_name)
        
        print('[INFO] Fetching additional news from Grok for ', bot_name.upper())
        grok_news = asyncio.run(fetch_grok_news(self=self,bot_name=bot_name))
        
        for index, grok_item in enumerate(grok_news, 1):
            print(f'[INFO] Processing Grok news item {index}/{len(grok_news)}')
            self.current_article_title = grok_item['title']
            self.current_raw_article_content = grok_item['content']
            
            article_info = WebScrapper.validate_and_save_article(
                self=self,
                news_link=f"Grok AI - " + grok_item['title'],
                category_id=category_id,
                bot_id=bot_id,
                bot_name=bot_name,
                article_title=grok_item['title'],
                category_slack_channel=category_slack_channel,
                article_content=grok_item['content'],
            )
            
            if 'error' in article_info:
                error_message = f"Failed to process Grok news item: {article_info['error']}"
                self.logger.error(error_message)
                result['errors'].append(error_message)
            elif 'message' in article_info:
                print(f"[INFO] : {article_info['message']}")

        end_time = datetime.now()
        execution_time = end_time - start_time
        print('[INFO] Total execution time: ', execution_time)
        return result
