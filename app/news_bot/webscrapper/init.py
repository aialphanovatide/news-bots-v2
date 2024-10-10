import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.news_bot.webscrapper.utils import clean_text, resolve_redirects_playwright, transform_string
from app.news_bot.webscrapper.webscrapper import WebScraper
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from config import Category
from .filters import filter_link, keywords_filter, last_10_article_checker, url_checker, datetime_checker
from .analyzer import analyze_content
from .image_generator import ImageGenerator
from .data_manager import DataManager
from config import db


# class NewsScraper:
#     def __init__(self, url, category_id, bot_id):
#         self.url = url
#         self.category_id = category_id
#         self.bot_id = bot_id
#         self.scraper = WebScraper(url)
#         self.data_manager = DataManager()
#         self.image_generator = ImageGenerator()
        
#     def process_url(self, link):
#         # Check if the URL has been processed before
#         url_check_result = url_checker(url=link, bot_id=self.bot_id)
#         if url_check_result is not None:
#             print(f"[INFO] URL already processed: {link}")
#             print(f"[INFO] Error: {url_check_result.get('error')}")
#             return False

#         # Filter the link
#         url_filter_result = filter_link(url=link)
#         if 'error' in url_filter_result:
#             print(f"[INFO] Error filtering URL: {link}")
#             print(f"[INFO] Error: {url_filter_result['error']}")
#             return False

#         if url_filter_result['response'] is None:
#             print(f"[INFO] URL filtered out: {link}")
#             return False

#         return True
        
#     def run(self):
#         """
#         Run the news scraping process.

#         This method scrapes news links, analyzes content, checks for similarity with recent articles,
#         filters based on keywords, generates summaries and images, and saves the processed articles.

#         Returns:
#         dict: A dictionary containing:
#             - 'message' (str): A summary of the operation result.
#             - 'articles_saved' (int): The number of articles successfully saved.
#             - 'unwanted_articles_saved' (int): The number of articles filtered out and saved as unwanted.
#             - 'error' (str, optional): Description of any error that occurred during processing.
#         """
#         # Scrape RSS feed and get news links along with their publication dates
#         news_items = self.scraper.scrape_rss()
#         category_id=self.category_id
#         articles_saved = 0
#         unwanted_articles_saved = 0
#         for item in news_items:
#             link = item['link']
#             pub_date = item['published']
            
#             try:
#                 print(f"[INFO] Analyzing URL: {link}")
#                 link = resolve_redirects_playwright(link)
#                 if not self.process_url(link):
#                     continue
                
#                 # Check if the article date is valid and recent
#                 if not datetime_checker(pub_date):
#                     print(f"[INFO] Article date is not recent or valid: {pub_date}")
#                     continue
                
#                 article_content = analyze_content(link)

#                 if article_content.get('success', False):
#                     paragraphs = article_content.get('paragraphs', [])
#                     article_text = " ".join(paragraphs)  
                    
#                     title = str(article_content.get('title', 'No title found')) 
#                     url = str(article_content.get('url', 'No URL found')) 
#                 else:
#                     print("[ERROR] - No content - No 200 Response.")
#                     continue
                
#                 # Similarity check
#                 similarity_check = last_10_article_checker(self.bot_id, article_text, title, url)
#                 if similarity_check.get('error'):
#                     print(f"[INFO] Article is similar to a recent one: {similarity_check['error']}")
#                     print(f"[INFO] Saved as unwanted article")
#                     unwanted_articles_saved += similarity_check['unwanted_articles_saved']
#                     continue

#                 # Keyword filtering
#                 result = keywords_filter(self.bot_id, article_text, title, url)
#                 if result['error'] is not None:
#                     unwanted_articles_saved += result['unwanted_articles_saved']
#                     continue
                
#                 used_keywords = result['used_keywords']
#                 if not used_keywords:
#                     print("[ERROR] No keywords found for this article - Rejected.")

#                 # Perplexity summary
#                 perplexity_result = article_perplexity_remaker(content=article_text, category_id=category_id)
#                 if not perplexity_result['success']:
#                     print(f"[ERROR] Perplexity error: {perplexity_result['error']}")
#                     return {
#                         'error': f'There is no summary, perplexity error {perplexity_result["error"]}',
#                         'articles_saved': articles_saved,
#                         'unwanted_articles_saved': unwanted_articles_saved
#                     }

#                 # Summary processing
#                 new_article_summary = perplexity_result['response']
#                 final_summary = clean_text(new_article_summary)
#                 lines = final_summary.splitlines()

#                 if lines:
#                     new_article_title = lines[0].strip() 
#                     final_summary = "\n".join(lines[1:]).strip()  
#                 else:
#                     new_article_title = title 

#                 # Generate image
#                 image_result = self.image_generator.generate_poster_prompt(article=new_article_summary, bot_id=self.bot_id)
#                 if not image_result['success']:
#                     print(f"[ERROR] Image generation failed: {image_result['error']}")
#                     return {
#                         'error': f'Image couldn\'t be generated: {image_result["error"]}',
#                         'articles_saved': articles_saved,
#                         'unwanted_articles_saved': unwanted_articles_saved
#                     }

#                 image = image_result['response']
#                 article_id = transform_string(new_article_title)
#                 final_filename = re.sub(r'[^a-zA-Z0-9]', '', article_id)
#                 image_filename = f"{final_filename}.jpg"

#                 # Resize and upload image
#                 resized_image_result = self.image_generator.resize_and_upload_image_to_s3(image, 'appnewsposters', image_filename)
#                 if not resized_image_result['success']:
#                     print(f"[ERROR] Image upload to AWS failed: {resized_image_result['error']}")
#                     return {
#                         'error': f'Image couldn\'t be uploaded to AWS: {resized_image_result["error"]}',
#                         'articles_saved': articles_saved,
#                         'unwanted_articles_saved': unwanted_articles_saved
#                     }
                
#                 image_url = resized_image_result['response']
                
#                 # Save the article to the database using data_manager
#                 article_data = {
#                     'title': new_article_title,
#                     'content': final_summary,
#                     'image': image_filename,
#                     'analysis': '',  # Add analysis if available
#                     'link': link,
#                     'date': datetime.now(),
#                     'used_keywords': ', '.join(used_keywords),
#                     'is_efficent': '', 
#                     'is_top_story': False,  # Set to True if it's a top story
#                     'bot_id': self.bot_id
#                 }

#                 try:
#                     new_article_id = self.data_manager.save_article(article_data)
#                     articles_saved += 1
#                     print(f"[SUCCESS] Article {new_article_title} saved with ID: {new_article_id}")
#                     category = db.session.query(Category).filter(Category.id == self.category_id).first()
#                     if category and category.slack_channel:
#                         slack_channel = category.slack_channel
#                         # Notify on Slack about the article
#                         send_NEWS_message_to_slack_channel(
#                             channel_id=slack_channel, 
#                             title=new_article_title,
#                             article_url=link,
#                             content=final_summary, 
#                             used_keywords=used_keywords, 
#                             image=image_url
#                         )

#                 except Exception as e:
#                     print(f"[ERROR] Failed to save article: {e}")
#                     return {
#                         'error': f"Failed to save article: {e}",
#                         'articles_saved': articles_saved,
#                         'unwanted_articles_saved': unwanted_articles_saved
#                     }

#             except Exception as e:
#                 print(f"[ERROR] An unexpected error occurred during article processing: {e}")
#                 return {
#                     'error': f"An unexpected error occurred during article processing: {e}",
#                     'articles_saved': articles_saved,
#                     'unwanted_articles_saved': unwanted_articles_saved
#                 }

#         return {
#             'message': f'{articles_saved} articles validated and saved',
#             'articles_saved': articles_saved,
#             'unwanted_articles_saved': unwanted_articles_saved
#         }




class NewsScraper:
    def __init__(self, url, category_id, bot_id, verbose=True, debug=False):
        self.url = url
        self.category_id = category_id
        self.bot_id = bot_id
        self.verbose = verbose
        self.debug = debug
        self.scraper = WebScraper(url)
        self.data_manager = DataManager()
        self.image_generator = ImageGenerator()
        self.logs_slack_channel_id = 'C06FTS38JRX'


    def log(self, message, level='info'):
        if self.verbose:
            if level == 'info':
                logging.info(message)
            elif level == 'error':
                logging.error(message)
            elif level == 'debug':
                logging.debug(message)
     
        
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
        news_items = self.scraper.scrape_rss()
        articles_saved = 0
        unwanted_articles_saved = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {executor.submit(self.process_item, item): item for item in news_items}
            for future in as_completed(future_to_item):
                result = future.result()
                if result.get('success', False):
                    articles_saved += result['articles_saved']
                    unwanted_articles_saved += result['unwanted_articles_saved']
                else:
                    self.log(f"Error processing item: {result.get('error')}", 'error')

        self.log(f"Completed news scraping process. Articles saved: {articles_saved}, Unwanted articles: {unwanted_articles_saved}", 'info')
        return {
            'success': True,
            'message': f'{articles_saved} articles validated and saved',
            'articles_saved': articles_saved,
            'unwanted_articles_saved': unwanted_articles_saved
        }

        
    def process_item(self, item):
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