from app.news_bot.webscrapper.webscrapper import WebScraper
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from .filters import datetime_checker, filter_link, last_10_article_checker, url_checker, content_filter
from .analyzer import analyze_content
from .image_generator import generate_image
from .data_manager import DataManager

class NewsScraper:
    def __init__(self, url, category_id, bot_id):
        self.url = url
        self.category_id = category_id
        self.bot_id = bot_id
        self.scraper = WebScraper(url)
        self.data_manager = DataManager()  
        
        
def run(self):
    news_links = self.scraper.scrape()
    for link in news_links:
        print(f"[INFO] Analyzing URL: {link}")
        # Check if the URL has been processed before
        url_check_result = url_checker(url=link, bot_id=self.bot_id)
        if url_check_result is not None:
            print(f"[INFO] URL already processed: {link}")
            print(f"[INFO] Error: {url_check_result.get('error')}")
            continue
        
        # Filter the link
        url_filter_result = filter_link(url=link)
        if 'error' in url_filter_result:
            print(f"[INFO] Error filtering URL: {link}")
            print(f"[INFO] Error: {url_filter_result['error']}")
            continue
        
        if url_filter_result['response'] is None:
            print(f"[INFO] URL filtered out: {link}")
            continue
            

        
        # Analyze the content of the article
        article_content = analyze_content(link)
        
        if not article_content.get('success', False):
            print(f"[ERROR] Failed to analyze content: {article_content.get('error')}")
            continue
        
        # Check similarity with last 10 articles
        similarity_check = last_10_article_checker(bot_id=self.bot_id,article_content=article_content['paragraphs'], title=article_content['title'],url=article_content['url'])
        
        if similarity_check.get('error'):
            print(f"[INFO] Article is similar to a recent one: {similarity_check['error']}")
            print(f"[INFO] Saved as unwanted article")
        else:
            print("[INFO] Article is not similar to recent ones")
            content = self.scraper.fetch_content(article_content['url'], article_content['title'],article_content['paragraphs'])
            
            
        print(f"[INFO] Unwanted articles saved in this run: {similarity_check['unwanted_articles_saved']}")

    print(f"[INFO] Finished processing all links for bot: {self.bot_id}")

    def run(self):
        news_links = self.scraper.scrape()
        for link in news_links:
            if not url_checker(link, bot_id=self.bot_id):
                print("URL A ANALIZAR", link)
                if not last_10_article_checker(self.bot_id):
                    print("No es similar")
                else:
                    print("guardado en unwanted.")
                #aca empieza a scrappear contenido de cada link. 
                # content = self.scraper.fetch_content(link)
                # if datetime_checker(content.date) and content_filter(content.text):
                #     analysis = analyze_content(content.text)
                #     image = generate_image(analysis)
                #     self.data_manager.save_article({
                #         'link': link,
                #         'content': content.text,
                #         'analysis': analysis,
                #         'image': image,
                #         'category_id': self.category_id,
                #         'bot_id': self.bot_id
                #     })
                #     send_NEWS_message_to_slack_channel(f"New article analyzed: {link}", "news_channel")
                # else:
                #     self.data_manager.save_unwanted_article({
                #         'link': link,
                #         'reason': 'Failed filters'
                #     })




        news_links = self.scraper.scrape()

