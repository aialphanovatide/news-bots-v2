from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import aiofiles
import re
import json
import os
import requests
from config import Bot, Keyword, Site, UnwantedArticle, Article, UsedKeywords, db
from app.services.slack.actions import send_INFO_message_to_slack_channel
from app.services.d3.dalle3 import generate_poster_prompt, resize_and_upload_image_to_s3

from app.services.perplexity.article_convert import article_perplexity_remaker

async def save_dict_to_json(data_dict, filename='data.json'):
    try:
        if os.path.exists(filename):
            index = 1
            while True:
                new_filename = f"{os.path.splitext(filename)[0]}_{index}.json"
                if not os.path.exists(new_filename):
                    filename = new_filename
                    break
                index += 1

        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data_dict, indent=4))
        print("Data saved to", filename)
    except Exception as e:
        print("Error:", e)
 

def validate_keywords(news_link, article_title, paragraphs_text, category_id, bot_id):
    articles_saved = 0
    unwanted_articles_saved = 0
    
    try:
        # Check if the URL has already been analyzed
        existing_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, url=news_link).first()
        existing_article = Article.query.filter_by(bot_id=bot_id, url=news_link).first()
        print(existing_unwanted_article, existing_article)
        if existing_unwanted_article or existing_article:
            print("URL already analyzed. Not valid to analyze.")
            return {'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}


        # Retrieve keywords related to the bot from the database
        bot_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
        bot_keyword_names = [keyword.name for keyword in bot_keywords]

        # Check for used keywords within the article content
        used_keywords = [keyword for keyword in bot_keyword_names if any(keyword.lower() in paragraph.lower() for paragraph in paragraphs_text)]

        # Perform perplexity analysis on the article
        perplexity_result = article_perplexity_remaker(paragraphs_text, category_id)
        
        # Extract title from perplexity results, if present
        title_match = re.search(r"\*\*(.*?)\*\*", perplexity_result)
        if title_match:
            slack_title = title_match.group(1)
            perplexity_result = re.sub(r"\*\*.*?\*\*", "", perplexity_result, count=1).strip()
        else:
            slack_title = article_title

        # Log analysis and title results
        print("Perplexity Result:", perplexity_result)
        print("Perplexity slack_title:", slack_title)

        if used_keywords:
            print(f"Matched Keywords: {', '.join(used_keywords)}")
            print("BOT ID: ", bot_id)
            
             # Save the article to the database
            new_article = Article(
                title=slack_title,
                content=perplexity_result,
                date=datetime.now(),
                url=news_link,
                bot_id=bot_id
            )
            db.session.add(new_article)
            db.session.commit()
            articles_saved += 1
            
            article_id = new_article.id
            image_filename = f"{article_id}.jpg"
            image = generate_poster_prompt(perplexity_result)
            image_url=f'https://apparticleimages.s3.us-east-2.amazonaws.com/{image_filename}'     
                        
            if image:
                try:
                    # Resize and upload the image to S3
                    resized_image_url = resize_and_upload_image_to_s3(image, 'apparticleimages', image_filename)

                    if resized_image_url:
                        print("Image resized and uploaded to S3 successfully.")
                    else:
                        print("Error resizing and uploading the image to S3.")
                except Exception as e:
                    print("Error:", e)
            else:
                print("Image not generated.")
                    
            # Notify on Slack about the article
            send_INFO_message_to_slack_channel(channel_id='C071142J72R', title=slack_title, content=perplexity_result, used_keywords=used_keywords, image=image_url)
            
            # Save the used keywords related to this article
            new_used_keyword = UsedKeywords(
                article_id=new_article.id,
                article_content=perplexity_result,
                article_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                article_url=news_link,
                keywords=', '.join(used_keywords),
                source='Google news',
                bot_id=bot_id
            )
            db.session.add(new_used_keyword)
            db.session.commit()
            
        else:
            # Save article deemed unwanted due to no keyword match
            unwanted_article = UnwantedArticle(
                title=article_title,
                content=paragraphs_text,
                analysis=perplexity_result,
                url=news_link,
                date=datetime.now(),
                used_keywords=None,
                is_article_efficent=None,
                bot_id=bot_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(unwanted_article)
            db.session.commit()
            
            unwanted_articles_saved += 1
            print("No matched keywords, saved to database.")
            

    except Exception as e:
        print(f"An unexpected error occurred during keyword validation: {str(e)}")

    return {'articles_saved': articles_saved, 'unwanted_articles_saved': unwanted_articles_saved}

async def fetch_url(news_link, category_id, title, bot_id) :
    try:
        # Obtain HTML content of the page
        article_response = requests.get(news_link)
        article_content_type = article_response.headers.get("Content-Type", "").lower()

        if 'text/html' not in article_content_type or article_response.status_code != 200:
            return {'url': news_link, 'title': None, 'paragraphs': [], 'error': f"Unable to retrieve content from {news_link}"}

        html = BeautifulSoup(article_response.text, 'html.parser')

        # Extract article title
        title_element = html.find('h1')
        article_title = title_element.text.strip() if title_element else title  # Fallback to the passed title if h1 not found

        # Extract paragraphs from the article
        paragraphs = html.find_all('p')
        paragraphs_text = [p.text.strip() for p in paragraphs]
        
        results = await validate_keywords(news_link, article_title, paragraphs_text, category_id, bot_id)

        print(f"Category ID {category_id} scraping process finished - {results['articles_saved']} articles saved in Article (DB), and {results['unwanted_articles_saved']} articles without matched keywords saved in Unwanted Articles (DB).")

        return {'url': news_link, 'title': article_title, 'paragraphs': paragraphs_text, 'message': 'Article successfully fetched and processed'}

    except Exception as e:
        return {'url': news_link, 'title': None, 'paragraphs': [], 'error': str(e)}
