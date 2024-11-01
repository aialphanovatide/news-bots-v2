import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.news_bot.webscrapper.utils import clean_text, resolve_redirects_playwright, transform_string
from app.news_bot.webscrapper.webscrapper import WebScraper
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from config import Category
from flask import current_app
from .filters import filter_link, keywords_filter, last_10_article_checker, url_checker, datetime_checker
from .analyzer import analyze_content
from .image_generator import ImageGenerator
from .data_manager import DataManager
from config import db


class NewsScraper:
    def __init__(self, url: str, category_id: int, bot_id: int, verbose: bool = True, debug: bool = False, app=None):
        self.url = url
        self.category_id = category_id
        self.bot_id = bot_id
        self.verbose = verbose
        self.app = app or current_app._get_current_object()
        self.debug = debug
        self.scraper = WebScraper(url)
        self.data_manager = DataManager()
        self.image_generator = ImageGenerator()
        self.logs_slack_channel_id = 'C06FTS38JRX'

        # Setup logger
        self.logger = self.setup_logger()
        self.logger.debug(f"NewsScraper initialized with URL: {url}, category_id: {category_id}, bot_id: {bot_id}")


    def setup_logger(self):
        logger = logging.getLogger(f"NewsScraper-{self.bot_id}")
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

        # Clear any existing handlers to avoid duplicate logs
        logger.handlers.clear()

        # Create a stream handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger


    def log(self, message, level='info'):
        if self.verbose:
            if level == 'info':
                self.logger.info(message)
            elif level == 'error':
                self.logger.error(message)
            elif level == 'debug':
                self.logger.debug(message)
     
        
    def process_url(self, link):
        # Check if the URL has been processed before
        url_check_result = url_checker(url=link, bot_id=self.bot_id)
        if url_check_result is not None:
            self.log(f"[INFO] URL already processed: {link}")
            self.log(f"[INFO] Error: {url_check_result.get('error')}")
            return False

        # Filter the link
        url_filter_result = filter_link(url=link)
        if 'error' in url_filter_result:
            self.log(f"[INFO] Error filtering URL: {link}")
            self.log(f"[INFO] Error: {url_filter_result['error']}")
            return False

        if url_filter_result['response'] is None:
            self.log(f"[INFO] URL filtered out: {link}")
            return False

        return True
    
    def run(self):
        self.log("Starting news scraping process", 'info')
        self.log(f"Bot ID: {self.bot_id}, Category ID: {self.category_id}", 'debug')
        news_items = self.scraper.scrape_rss()
        self.log(f"Number of news items scraped: {len(news_items)}", 'debug')
        articles_saved = 0
        unwanted_articles_saved = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            self.log(f"Starting ThreadPoolExecutor with max_workers=10", 'debug')
            future_to_item = {executor.submit(self.process_item, item): item for item in news_items}
            self.log(f"Submitted {len(future_to_item)} items for processing", 'debug')
            for future in as_completed(future_to_item):
                self.log("Processing completed future", 'debug')
                result = future.result()
                if result.get('success', False):
                    articles_saved += result['articles_saved']
                    unwanted_articles_saved += result['unwanted_articles_saved']
                    self.log(f"Processed item successfully. Articles saved: {result['articles_saved']}, Unwanted articles: {result['unwanted_articles_saved']}", 'debug')
                else:
                    self.log(f"Error processing item: {result.get('error')}", 'error')
                self.log(f"Current totals - Articles saved: {articles_saved}, Unwanted articles: {unwanted_articles_saved}", 'debug')

        self.log(f"Completed news scraping process. Articles saved: {articles_saved}, Unwanted articles: {unwanted_articles_saved}", 'info')
        return {
            'success': True,
            'message': f'{articles_saved} articles validated and saved',
            'articles_saved': articles_saved,
            'unwanted_articles_saved': unwanted_articles_saved
        }

        
    def process_item(self, item):
        with self.app.app_context():
            link = item['link']
            pub_date = item['published']

            try:
                self.log(f"Analyzing URL: {link}", 'debug')
                link = resolve_redirects_playwright(link)
                if not self.process_url(link) or not datetime_checker(pub_date):
                    return {'success': True, 'articles_saved': 0, 'unwanted_articles_saved': 0}

                article_content = analyze_content(link)
                if not article_content.get('success', False):
                    self.log("No content - No 200 Response.", 'error')
                    return {'success': True, 'articles_saved': 0, 'unwanted_articles_saved': 0}

                article_text = " ".join(article_content.get('paragraphs', []))
                title = str(article_content.get('title', 'No title found'))
                url = str(article_content.get('url', 'No URL found'))

                # Similarity check
                similarity_check = last_10_article_checker(self.bot_id, article_text, title, url)
                if similarity_check.get('error'):
                    self.log(f"Article is similar to a recent one: {similarity_check['error']}", 'info')
                    return {'success': True, 'articles_saved': 0, 'unwanted_articles_saved': 1}

                # Keyword filtering
                result = keywords_filter(self.bot_id, article_text, title, url)
                if result['error'] is not None:
                    return {'success': True, 'articles_saved': 0, 'unwanted_articles_saved': 1}

                used_keywords = result['used_keywords']
                if not used_keywords:
                    self.log("No keywords found for this article - Rejected.", 'info')
                    return {'success': True, 'articles_saved': 0, 'unwanted_articles_saved': 1}

                # Perplexity summary
                perplexity_result = article_perplexity_remaker(content=article_text, category_id=self.category_id)
                if not perplexity_result['success']:
                    self.log(f"Perplexity error: {perplexity_result['error']}", 'error')
                    return {'success': False, 'error': f'There is no summary, perplexity error {perplexity_result["error"]}'}

                # Summary processing
                new_article_summary = perplexity_result['response']
                final_summary = clean_text(new_article_summary)
                lines = final_summary.splitlines()

                if lines:
                    new_article_title = lines[0].strip() 
                    final_summary = "\n".join(lines[1:]).strip()  
                else:
                    new_article_title = title 

                # Generate image
                image_result = self.image_generator.generate_poster_prompt(article=new_article_summary, bot_id=self.bot_id)
                if not image_result['success']:
                    self.log(f"Image generation failed: {image_result['error']}", 'error')
                    return {'success': False, 'error': f'Image couldn\'t be generated: {image_result["error"]}'}

                image = image_result['response']
                article_id = transform_string(new_article_title)
                final_filename = re.sub(r'[^a-zA-Z0-9]', '', article_id)
                image_filename = f"{final_filename}.jpg"

                # Resize and upload image
                resized_image_result = self.image_generator.resize_and_upload_image_to_s3(image, 'appnewsposters', image_filename)
                if not resized_image_result['success']:
                    self.log(f"Image upload to AWS failed: {resized_image_result['error']}", 'error')
                    return {'success': False, 'error': f'Image couldn\'t be uploaded to AWS: {resized_image_result["error"]}'}
                
                image_url = resized_image_result['response']
                
                # Save the article to the database using data_manager
                article_data = {
                    'title': new_article_title,
                    'content': final_summary,
                    'image': image_filename,
                    'analysis': '',
                    'link': link,
                    'date': datetime.now(),
                    'used_keywords': ', '.join(used_keywords),
                    'is_efficent': '', 
                    'is_top_story': False,
                    'bot_id': self.bot_id
                }

                try:
                    new_article_id = self.data_manager.save_article(article_data)
                    self.log(f"Article {new_article_title} saved with ID: {new_article_id}", 'info')
                    category = db.session.query(Category).filter(Category.id == self.category_id).first()
                    if category and category.slack_channel:
                        slack_channel = category.slack_channel
                        # Notify on Slack about the article
                        send_NEWS_message_to_slack_channel(
                            channel_id=self.logs_slack_channel_id if self.debug else slack_channel, 
                            title=new_article_title,
                            article_url=link,
                            content=final_summary, 
                            used_keywords=used_keywords, 
                            image=image_url
                        )
                    return {'success': True, 'articles_saved': 1, 'unwanted_articles_saved': 0}

                except Exception as e:
                    self.log(f"Failed to save article: {e}", 'error')
                    return {'success': False, 'error': f"Failed to save article: {e}"}

            except Exception as e:
                self.log(f"An unexpected error occurred during article processing: {e}", 'error')
                return {'success': False, 'error': f"An unexpected error occurred during article processing: {e}"}


