import re
import os
import logging
from config import db
from config import Category
from datetime import datetime
from flask import current_app
from .data_manager import DataManager
from .analyzer import analyze_content
from .image_generator import ImageGenerator
from logging.handlers import RotatingFileHandler
from app.news_bot.webscrapper.webscrapper import WebScraper
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.news_bot.webscrapper.utils import clean_text, resolve_redirects_playwright, transform_string
from app.news_bot.webscrapper.filters import filter_link, keywords_filter, last_10_article_checker, is_url_analyzed, datetime_checker


class NewsScraper:
    def __init__(self, url: str, category_id: int, bot_id: int, verbose: bool = True, debug: bool = False, app=None):
        self.url = url
        self.debug = debug
        self.bot_id = bot_id
        self.verbose = verbose
        self.category_id = category_id
        self.scraper = WebScraper(url)
        self.data_manager = DataManager()
        self.image_generator = ImageGenerator()
        self.logs_slack_channel_id = 'C06FTS38JRX'
        self.app = app or current_app._get_current_object()

        # Setup logger
        self.logger = self.setup_logger()
        self.logger.debug(f"NewsScraper initialized with URL: {url}, category_id: {category_id}, bot_id: {bot_id}")


    def setup_logger(self):
        """Configure logger with both file and console handlers.
        
        Creates a logger that:
        - Writes to a bot-specific log file in a logs directory
        - Outputs to console with different levels based on debug mode
        - Uses rotation to manage log file size
        - Includes timestamp, logger name, level, and message
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(current_app.root_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logger
        logger = logging.getLogger(f"NewsScraper-{self.bot_id}")
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Common formatter for both handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler with rotation
        log_file = os.path.join(log_dir, f'bot_{self.bot_id}.log')
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log debug to file
        file_handler.setFormatter(formatter)
        
        # Add both handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        logger.debug(f"Logger initialized for bot {self.bot_id}")
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
        if is_url_analyzed(url=link, bot_id=self.bot_id):
            self.log(f"URL already processed: {link}")
            return False

        # Filter the link
        url_filter_result = filter_link(url=link)
        if 'error' in url_filter_result:
            self.log(f"Error filtering URL: {link}")
            self.log(f"Error: {url_filter_result['error']}")
            return False

        if url_filter_result['response'] is None:
            self.log(f"URL filtered out: {link}")
            return False

        return True

    def run(self):
        """Execute the news scraping process with parallel article processing.
        
        This method:
        1. Scrapes RSS feed for news items
        2. Processes items in parallel using ThreadPoolExecutor
        3. Tracks successful and unwanted articles
        4. Handles errors and logging throughout the process
        
        Process Flow:
        - Fetch RSS items
        - Create thread pool for parallel processing
        - Process each item (analyze, filter, save)
        - Track results and handle errors
        - Summarize final results
        
        Returns:
            dict: Process results containing:
                - success (bool): Overall success status
                - message (str): Summary message
                - articles_saved (int): Count of saved articles
                - unwanted_articles_saved (int): Count of filtered articles
        
        Note:
            Uses ThreadPoolExecutor for parallel processing with a maximum
            of 15 concurrent workers to balance performance and resource usage.
        """
        self.log("Starting News Scraping process", 'info')
        self.log(f"Bot ID: {self.bot_id}, Category ID: {self.category_id}", 'debug')
        
        try:
            # Fetch RSS items
            news_items = self.scraper.scrape_rss()
            self.log(f"Retrieved {len(news_items)} news items from RSS feed", 'info')
            
            articles_saved = 0
            unwanted_articles_saved = 0

            # Process items in parallel
            with ThreadPoolExecutor(max_workers=15) as executor:
                self.log(f"Initializing parallel processing with {executor._max_workers} workers", 'debug')
                future_to_item = {
                    executor.submit(self.process_item, item): item 
                    for item in news_items
                }
                
                # Process completed futures
                for future in as_completed(future_to_item):
                    try:
                        result = future.result()
                        
                        if result.get('success', False):
                            articles_saved += result['articles_saved']
                            unwanted_articles_saved += result['unwanted_articles_saved']
                            self.log(
                                f"Item processed - Saved: {result['articles_saved']}, "
                                f"Filtered: {result['unwanted_articles_saved']}", 
                                'debug'
                            )
                        else:
                            self.log(f"Processing error: {result.get('error')}", 'error')
                            
                    except Exception as e:
                        self.log(f"Future processing error: {str(e)}", 'error')
                        
                    # Log progress
                    self.log(
                        f"Progress - Saved: {articles_saved}, Filtered: {unwanted_articles_saved}", 
                        'debug'
                    )

            # Log final results
            self.log(
                f"Completed processing - Total saved: {articles_saved}, "
                f"Total filtered: {unwanted_articles_saved}", 
                'info'
            )
            
            return {
                'success': True,
                'message': f'{articles_saved} articles validated and saved',
                'articles_saved': articles_saved,
                'unwanted_articles_saved': unwanted_articles_saved
            }
            
        except Exception as e:
            error_msg = f"News scraping process failed: {str(e)}"
            self.log(error_msg, 'error')
            return {
                'success': False,
                'message': error_msg,
                'articles_saved': 0,
                'unwanted_articles_saved': 0
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
                perplexity_result = article_perplexity_remaker(content=article_text, bot_id=self.bot_id)
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


