import re
import ssl
import aiohttp
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from app.utils.helpers import transform_string
from config import Keyword, UnwantedArticle, Article, UsedKeywords, db
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.d3.dalle3 import generate_poster_prompt, resize_and_upload_image_to_s3


# validate a link against a list of keyword and then saves it to the DB
def validate_and_save_article(news_link, article_title, article_content, category_id, bot_id):
    
    articles_saved = 0
    unwanted_articles_saved = 0
    
    try:
        # Check if the URL has already been analyzed
        existing_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, url=news_link).first()
        existing_article = Article.query.filter_by(bot_id=bot_id, url=news_link).first()
      
        if existing_unwanted_article or existing_article:
            return {'error': 'article already analyzed', 
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved}

        # Retrieve keywords related to the bot from the database
        bot_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
        bot_keyword_names = [keyword.name for keyword in bot_keywords]

        # Check for used keywords within the article content
        used_keywords = [keyword for keyword in bot_keyword_names if any(keyword.lower() in paragraph.lower() for paragraph in article_content)]
        
        if not used_keywords:
            # Save article right away because there was no matched keywords
            unwanted_article = UnwantedArticle(
                title=article_title,
                content=article_content,
                url=news_link,
                date=datetime.now(),
                reason='article did not has any keyword',
                bot_id=bot_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(unwanted_article)
            db.session.commit()
            
            unwanted_articles_saved += 1
            return {'error': f"article {article_title} didn't match any keyword", 
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved}

        # Perform perplexity summary on the article
        perplexity_result = article_perplexity_remaker(content=article_content, 
                                                       category_id=category_id)
        
        # if there's no summary, then return so the bot tries in the next execution
        if perplexity_result['success'] == False:
            return {'error': f'There is no summary, perplexity error {perplexity_result["error"]}', 
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved}

        new_article_summary = perplexity_result['response']
        # Extract title from perplexity results, if present
        title_match = re.search(r"\*\*(.*?)\*\*", new_article_summary)
        new_article_title = article_title
        if title_match and new_article_summary:
            new_article_title = title_match.group(1)
            new_article_summary = re.sub(r"\*\*.*?\*\*", "", new_article_summary, count=1).strip()
            
        # Log analysis and title results
        # print("\nPerplexity new_article_title:", new_article_title)
        # print("\nPerplexity Result:", new_article_summary)
        # print(f"\nMatched Keywords: {', '.join(used_keywords)}")
        # print("BOT ID: ", bot_id)


        image = generate_poster_prompt(article=new_article_summary, bot_id=bot_id)
        # if image generation fails, then return so the bot tries in the next execution
        if image['success'] == False:
            return {'error': f'Image couldnt be generated: {image["error"]}', 
                'articles_saved': articles_saved,
                'unwanted_articles_saved': unwanted_articles_saved}
        
        image = image['response']
        article_id = transform_string(new_article_title)
        image_filename = f"{article_id}.jpg"
        image_url=f'https://apparticleimages.s3.us-east-2.amazonaws.com/{image_filename}'     
                    
        try:
            # Resize and upload the image to S3
            resized_image_url = resize_and_upload_image_to_s3(image, 'apparticleimages', image_filename)
            if resized_image_url['success'] == False:
                return {'error': f'Image couldnt be upload to AWS: {resized_image_url["error"]}', 
                'articles_saved': articles_saved,
                'unwanted_articles_saved': unwanted_articles_saved}
        except Exception as e:
            return {'error': 'Unexpected error while uploading image to AWS', 
                'articles_saved': articles_saved,
                'unwanted_articles_saved': unwanted_articles_saved}
        
        # Save the article to the database
        new_article = Article(
            title=new_article_title,
            content=new_article_summary,
            image=image_url,
            date=datetime.now(),
            url=news_link,
            used_keywords=', '.join(used_keywords),
            bot_id=bot_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(new_article)
        db.session.commit()
        articles_saved += 1
                
        # Notify on Slack about the article
        send_NEWS_message_to_slack_channel(channel_id='C071142J72R', 
                                           title=new_article_title,
                                           article_url=news_link,
                                           content=new_article_summary, 
                                           used_keywords=used_keywords, 
                                           image=image_url)
        
        return {'message': f'article {new_article_title} validated and saved', 
                'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}
            
      
    except Exception as e:
        return {'error': f"An unexpected error occurred during keyword validation: {str(e)}", 
                'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}



async def fetch_article_content(news_link: str, category_id: int, title: str, bot_id: int, bot_name: str) -> Dict[str, Any]:
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl.SSLContext())) as session:
            async with session.get(news_link) as response:
                if response.status != 200:
                    return {
                    'success': False,
                    'url': news_link,
                    'title': None,
                    'paragraphs': [],
                    'error': f"HTTP error: {response.status} - {response.reason}"
                    }
    
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    return {'success': False, 'url': news_link, 'title': None, 'paragraphs': [], 'error': "Content is not HTML"}

                text = await response.text()
        
        # Parse HTML content with BeautifulSoup
        html = BeautifulSoup(text, 'html.parser')

        # Extract article title
        title_element = html.find('h1')
        article_title = title_element.text.strip() if title_element else title  # Fallback to the passed title if h1 not found

        # Extract paragraphs from the article
        paragraphs = html.find_all('p')
        article_content = [p.text.strip() for p in paragraphs]

        # Validate and process the content
        result = validate_and_save_article(news_link, article_title, article_content, category_id, bot_id)
        if 'error' in result:
            return {'success': False, 'url': news_link, 'title': article_title, 
                    'paragraphs': article_content, 'error': result['error']}

        return {'success': True, 'url': news_link, 'title': article_title, 'paragraphs': article_content, 'message': result['message']}

    except aiohttp.ClientError as e:
        return {'success': False, 'url': news_link, 'title': None, 'paragraphs': [], 'error': f"Client error: {e}"}
    except Exception as e:
        return {'success': False, 'url': news_link, 'title': None, 'paragraphs': [], 'error': f'Error while getting article content: {str(e)}'}

