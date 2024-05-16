import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import Keyword, UnwantedArticle, Article, UsedKeywords, db
# from app.services.slack.actions import send_INFO_message_to_slack_channel
from app.services.d3.dalle3 import generate_poster_prompt, resize_and_upload_image_to_s3
from app.services.perplexity.article_convert import article_perplexity_remaker

 
# 
def validate_keywords(news_link, article_title, article_content, category_id, bot_id):
    
    articles_saved = 0
    unwanted_articles_saved = 0
    
    try:
        # Check if the URL has already been analyzed
        existing_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, url=news_link).first()
        existing_article = Article.query.filter_by(bot_id=bot_id, url=news_link).first()
      
        if existing_unwanted_article or existing_article:
            return {'response': 'article already analyzed', 
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved}


        # Retrieve keywords related to the bot from the database
        bot_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
        bot_keyword_names = [keyword.name for keyword in bot_keywords]
        print('bot_keyword_names: ', bot_keyword_names)

        # Check for used keywords within the article content
        used_keywords = [keyword for keyword in bot_keyword_names if any(keyword.lower() in paragraph.lower() for paragraph in article_content)]

        # Perform perplexity analysis on the article
        perplexity_result = article_perplexity_remaker(content=article_content, 
                                                       category_id=category_id)
        
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
            
            if image['success'] == False:
                # Send a message to slack
                print(f'Image couldnt be generated: {str(image['error'])}')

            image = image['response']
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
            # send_INFO_message_to_slack_channel(channel_id='C071142J72R', title=slack_title, content=perplexity_result, used_keywords=used_keywords, image=image_url)
            
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
                content=article_content,
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
        article_content = [p.text.strip() for p in paragraphs]
        
        results = await validate_keywords(news_link, article_title, article_content, category_id, bot_id)

        print(f"Category ID {category_id} scraping process finished - {results['articles_saved']} articles saved in Article (DB), and {results['unwanted_articles_saved']} articles without matched keywords saved in Unwanted Articles (DB).")

        return {'url': news_link, 'title': article_title, 'paragraphs': article_content, 'message': 'Article successfully fetched and processed'}

    except Exception as e:
        return {'url': news_link, 'title': None, 'paragraphs': [], 'error': str(e)}
