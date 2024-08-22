import logging
import os
from typing import Dict, Any, List
from flask import current_app
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import re
from app.news_bot.s3 import generate_and_upload_image
from app.services.perplexity.article_convert import article_perplexity_remaker
from config import Bot
from app.news_bot.webscrapper.utils import clean_text, transform_string

class WebScrapper:
    def __init__(self, bot_id: int, bot_name: str, db_session):
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.db_session = db_session
        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger(f"WebScrapper-{self.bot_name}")
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def get_news_sources(self) -> List[Dict[str, Any]]:
        bot = self.db_session.query(Bot).filter_by(id=self.bot_id).first()
        if not bot:
            self.logger.error(f"Bot with ID {self.bot_id} not found")
            return []

        sources = []
        for site in bot.sites:
            sources.append({
                'url': site.url,
                'bot_id': site.bot_id,
                'category_id': bot.category_id,
                'blacklist': [bl_word.name for bl_word in bot.blacklist],
                'category_slack_channel': site.category_slack_channel
            })

        return sources

    def fetch_urls(self, url: str) -> Dict:
        print(f"[INFO] Starting URL fetch from: {url}")
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

                links = page.query_selector_all('a[href*="./read/"]')
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
            error_message = f"Exception in fetch_urls: {str(e)}"
            self.logger.error(error_message)
            result['errors'].append(error_message)
            return result

    def fetch_news(self):
        sources = self.get_news_sources()
        for source in sources:
            self.fetch_news_links(
                url=source['url'],
                bot_name=self.bot_name,
                blacklist=source.get('blacklist', []),
                category_id=source['category_id'],
                bot_id=self.bot_id,
                category_slack_channel=source.get('category_slack_channel')
            )

    def fetch_article_content(newsbot, news_link: str, category_id: int, title: str, bot_id: int, bot_name: str, category_slack_channel) -> Dict[str, Any]:
        newsbot.logger.info(f"Fetching article content for: {news_link}")
        print(newsbot.current_article_title )
        try:
            response = requests.get(news_link, timeout=10)
            newsbot.logger.info(f"Received response with status code: {response.status_code}")

            if response.status_code != 200:
                return {
                    'success': False,
                    'url': news_link,
                    'title': title,
                    'paragraphs': [],
                    'error': f"HTTP error: {response.status_code} - {response.reason}"
                }

            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                newsbot.logger.error(f"Content is not HTML for URL: {news_link}")
                return {'success': False, 'url': news_link, 'title': title, 
                        'paragraphs': [], 'error': "Content is not HTML"}

            html = BeautifulSoup(response.text, 'html.parser')
            title_element = html.find('h1')
            article_title = title_element.text.strip() if title_element else title
            newsbot.logger.info(f"Article title: {article_title}")

            if not article_title:
                newsbot.logger.error("Extracted article title is empty or None")
                return {'success': False, 'url': news_link, 'title': title, 
                        'paragraphs': [], 'error': "Article title is empty or None"}

            paragraphs = html.find_all('p')
            article_content = [p.text.strip() for p in paragraphs if p.text.strip()]
            newsbot.logger.info(f"Extracted {len(article_content)} paragraphs")

            publication_date = None
            date_elements = html.find_all(['span', 'date', 'time'])
            for date_element in date_elements:
                date_text = date_element.get('datetime') or date_element.text.strip()
                try:
                    publication_date = datetime.strptime(date_text, '%b %d, %Y at %I:%M %p')
                    break
                except (ValueError, TypeError):
                    try:
                        publication_date = datetime.strptime(date_text, '%Y-%m-%d')
                        break
                    except (ValueError, TypeError):
                        continue

            newsbot.logger.info(f"Publication date: {publication_date}")
            if publication_date and datetime.now() - publication_date > timedelta(days=1):
                newsbot.logger.error(f"Article is older than 24 hours: {publication_date}")
                return {'success': False, 'url': news_link, 'title': article_title, 
                        'paragraphs': article_content, 'error': 'Article is older than 24 hours'}
                
            # Establecer y registrar el título del artículo
            newsbot.current_article_title = article_title
            newsbot.logger.info(f"Setting current article title: {newsbot.current_article_title}")

            result = WebScrapper.validate_and_save_article(newsbot, news_link, article_title, article_content, 
                                                    category_id, bot_id, bot_name, category_slack_channel)

            if 'error' in result:
                return {'success': False, 'url': news_link, 'title': article_title, 
                        'paragraphs': article_content, 'error': result['error']}

            newsbot.logger.info(f"Article processed successfully: {result['message']}")
            return {'success': True, 'url': news_link, 'title': article_title, 
                    'paragraphs': article_content, 'message': result['message']}

        except requests.RequestException as e:
            newsbot.logger.error(f"Request error for {news_link}: {e}")
            return {'success': False, 'url': news_link, 'title': None, 
                    'paragraphs': [], 'error': f"Request error: {e}"}
        except Exception as e:
            newsbot.logger.error(f"Unexpected error while processing {news_link}: {e}")
            return {'success': False, 'url': news_link, 'title': None, 
                    'paragraphs': [], 'error': f'Error while getting article content: {str(e)}'}

    
    def validate_and_save_article(newsbot, news_link: str, article_title: str, article_content: Any, category_id: int, bot_id: int, bot_name: str, category_slack_channel: str) -> Dict[str, Any]:
        from app.news_bot.index import NewsBot

        print(f"\n[INFO] Validating and saving article: {news_link}")

        articles_saved = 0
        unwanted_articles_saved = 0
        raw_article_content = article_content if isinstance(article_content, str) else " ".join(article_content)

        try:
            with current_app.app_context():
                # Instanciar NewsBot
                news_bot = NewsBot(bot_id=bot_id, bot_name=bot_name, db_session=newsbot.db_session)

                if news_bot.is_url_article_already_analyzed(news_link):
                    print(f"[INFO] Article already analyzed: {news_link}")
                    return {'error': 'Article already analyzed', 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                similarity_validation = news_bot.validate_article_similarity(article_content, news_link, bot_id)
                if similarity_validation.get('error'):
                    print(f"[INFO] Similarity validation failed: {similarity_validation['error']}, link: {news_link}")
                    return {'error': similarity_validation['error'], 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                keyword_validation_result = news_bot.validate_keywords(article_content, article_title)
                if keyword_validation_result.get('error'):
                    print(f"[INFO] Keyword validation failed: {keyword_validation_result['error']}, link: {news_link}")
                    return {'error': keyword_validation_result['error'], 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                blacklist_validation_result = news_bot.validate_blacklist_keywords(article_content, article_title)
                if blacklist_validation_result.get('error'):
                    print(f"[INFO] Blacklist validation failed: {blacklist_validation_result['error']}, link: {news_link}")
                    return {'error': blacklist_validation_result['error'], 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                perplexity_result = article_perplexity_remaker(content=article_content, category_id=category_id)
                if not perplexity_result['success']:
                    print(f"[ERROR] Perplexity summary generation failed: {perplexity_result['error']}")
                    return {'error': f'No summary generated, perplexity error: {perplexity_result["error"]}', 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                new_article_summary = perplexity_result['response']
                final_summary = clean_text(new_article_summary)

                title_match = re.search(r"\*\*(.*?)\*\*", final_summary)
                new_article_title = title_match.group(1) if title_match else article_title
                final_summary = re.sub(r"\*\*.*?\*\*", "", final_summary, count=1).strip()
                news_bot.current_article_title = new_article_title
                image_result = generate_and_upload_image(newsbot, new_article_summary)
                
                if 'error' in image_result:
                    print(f"[ERROR] Image generation/upload failed: {image_result['error']}")
                    return {'error': image_result['error'], 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                image_url = image_result['image_url']

                
                newsbot.current_raw_article_content = raw_article_content
                newsbot.current_news_link = news_link
                newsbot.current_used_keywords = keyword_validation_result['message']
                save_result = news_bot.validate_and_save_article_data(
                    new_article_title, final_summary, re.sub(r'[^a-zA-Z0-9]', '', transform_string(new_article_title)) + '.png', news_link, newsbot.current_used_keywords)
                if 'error' in save_result:
                    print(f"[ERROR] Saving article data failed: {save_result['error']}")
                    return {'error': save_result['error'], 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

                articles_saved += 1

                print(f"[SUCCESS] Article {new_article_title} validated and saved")
                return {'message': f'Article {new_article_title} validated and saved', 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

        except Exception as e:
            print(f"[ERROR] Unexpected error during validation and saving: {e}")
            return {'error': f'Unexpected error during validation and saving: {e}', 'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}
