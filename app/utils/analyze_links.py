import re
import pdb
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Dict, Any
from flask import current_app
from app.utils.helpers import transform_string
from app.utils.similarity import cosine_similarity_with_openai_classification
from config import Blacklist, Keyword, UnwantedArticle, Article, db
from app.services.slack.actions import send_NEWS_message_to_slack_channel
from app.services.perplexity.article_convert import article_perplexity_remaker
from app.services.d3.dalle3 import generate_poster_prompt, resize_and_upload_image_to_s3

btc_slack_channel_id = 'C05RK7CCDEK'
eth_slack_channel_id = 'C05URLDF3JP'
hacks_slack_channel_id = 'C05UU8JBKKN'
layer_1_lmc_slack_channel_id = 'C05URM66B5Z'
layer_0_slack_channel_id = 'C05URM3UY8K'
layer_2_slack_channel = 'C05UB8G8B0F'
layer_1_mmc_slack_channel_id = 'C067ZA4GGNM'
cross_border_payment_slack_channel = 'C067P4CNC92'
lsd_slack_channel_id = 'C05UNS3M8R3'
oracles_slack_channel = 'C0600Q7UPS4'
defi_slack_channel = 'C067P43P8MA'
defi_perpetual_slack_channel = 'C05UU8EKME0'
defi_others_slack_channel = 'C067HNE4V0D'
ai_slack_channel = 'C067E1LJYKY'
gold_slack_channel = 'C074ZDTMYDA'
test_slack_channel = 'C071142J72R'

def clean_text(text):
    text = re.sub(r'Headline:\n', '', text)
    text = re.sub(r'Summary:\n', '', text)
    text = re.sub(r'Summary:', '', text)
    text = re.sub(r'\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*\s*\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\#\#\#', '', text, flags=re.MULTILINE)
    return text

def validate_yahoo_date(html: BeautifulSoup) -> bool:
    """
    Validate the freshness of a Yahoo article based on the <time> tag.

    Args:
        html (BeautifulSoup): Parsed HTML content.

    Returns:
        bool: True if the article is fresh (within the last 24 hours), False otherwise.
    """
    time_tag = html.find('time', {'datetime': True})
    if time_tag:
        date_time_str = time_tag['datetime']
        try:
            publication_date = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Check if the publication date is within the last 24 hours
            if datetime.utcnow() - publication_date <= timedelta(days=1):
                return True
        except ValueError as e:
            print(f"Error parsing date: {e}")
    return False 


def validate_and_save_article(news_link, article_title, article_content, category_id, bot_id, bot_name, category_slack_channel):
    print(f"\n[INFO] Validating and saving article: {news_link}")

    articles_saved = 0
    unwanted_articles_saved = 0
    raw_article_content = article_content

    try:
        with current_app.app_context():
            # Check if the URL has already been analyzed
            existing_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, url=news_link).first()
            existing_article = Article.query.filter_by(bot_id=bot_id, url=news_link).first()

            if existing_unwanted_article or existing_article:
                print(f"[INFO] Article already analyzed: {news_link}")
                return {
                    'error': 'article already analyzed',
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            # Ensure article_content is a single string
            if isinstance(article_content, list):
                article_content = " ".join(article_content)

            # Retrieve the last 10 articles
            last_10_articles = Article.query.filter_by(bot_id=bot_id).order_by(Article.date.desc()).limit(10).all()
            last_10_contents = [article.content for article in last_10_articles]

            # Check for high similarity using OpenAI cosine similarity function
            for content in last_10_contents:
                try:
                    similarity_score = cosine_similarity_with_openai_classification(content, article_content)
                    if similarity_score >= 0.85:
                        print(f"[INFO] Article too similar to recent articles: {news_link}")
                        unwanted_article = UnwantedArticle(
                            title=article_title,
                            content=raw_article_content,
                            url=news_link,
                            date=datetime.now(),
                            reason='article content too similar to recent articles',
                            bot_id=bot_id,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db.session.add(unwanted_article)
                        db.session.commit()
                        unwanted_articles_saved += 1
                        return {
                            'error': f"article {article_title} is too similar to a recent article",
                            'articles_saved': articles_saved,
                            'unwanted_articles_saved': unwanted_articles_saved
                        }
                except Exception as e:
                    print(f"[ERROR] Exception occurred during similarity check: {str(e)}")

            # Retrieve keywords related to the bot from the database
            bot_keywords = Keyword.query.filter_by(bot_id=bot_id).all()
            bot_keyword_names = [keyword.name for keyword in bot_keywords]

            bot_bl_keywords = Blacklist.query.filter_by(bot_id=bot_id).all()
            bot_bl_keyword_names = [bl_keyword.name for bl_keyword in bot_bl_keywords]

            # Check for used keywords within the article content
            used_keywords = [keyword for keyword in bot_keyword_names if keyword.lower() in article_content.lower()]

            # Check for blacklist keywords within the article content
            used_blacklist_keywords = [bl_keyword for bl_keyword in bot_bl_keyword_names if bl_keyword.lower() in article_content.lower()]
        
            if not used_keywords or used_blacklist_keywords:
                print(f"[INFO] Article did not match any keyword or contains blacklist keyword: {news_link}")
                unwanted_article = UnwantedArticle(
                    title=article_title,
                    content=raw_article_content,
                    url=news_link,
                    date=datetime.now(),
                    reason='article did not match any keyword or contains blacklist keyword',
                    bot_id=bot_id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(unwanted_article)
                db.session.commit()
                unwanted_articles_saved += 1
                return {
                    'error': f"article {article_title} didn't match any keyword or contains blacklist keyword",
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            # Perform perplexity summary on the article
            perplexity_result = article_perplexity_remaker(content=article_content, category_id=category_id)
            if not perplexity_result['success']:
                print(f"[ERROR] Perplexity error: {perplexity_result['error']}")
                return {
                    'error': f'There is no summary, perplexity error {perplexity_result["error"]}',
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            new_article_summary = perplexity_result['response']
            final_summary = clean_text(new_article_summary)

            # Extract title from perplexity results, if present
            title_match = re.search(r"\*\*(.*?)\*\*", final_summary)
            new_article_title = article_title
            if title_match:
                new_article_title = title_match.group(1)
                final_summary = re.sub(r"\*\*.*?\*\*", "", final_summary, count=1).strip()

            # Check if the Content has already been analyzed
            old_unwanted_article = UnwantedArticle.query.filter_by(bot_id=bot_id, title=new_article_title).first()
            old_article = Article.query.filter_by(bot_id=bot_id, title=new_article_title).first()

            if old_unwanted_article or old_article:
                print(f"[INFO] Article already analyzed: {new_article_title}")
                return {
                    'error': 'article already analyzed',
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            image = generate_poster_prompt(article=new_article_summary, bot_id=bot_id)
            if not image['success']:
                print(f"[ERROR] Image generation failed: {image['error']}")
                return {
                    'error': f'Image couldn\'t be generated: {image["error"]}',
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            image = image['response']
            article_id = transform_string(new_article_title)
            final_filename = re.sub(r'[^a-zA-Z0-9]', '', article_id)
            image_filename = f"{final_filename}.jpg"
            image_url = f'https://sitesnewsposters.s3.us-east-2.amazonaws.com/{image_filename}'

            try:
                # Resize and upload the image to S3
                resized_image_url = resize_and_upload_image_to_s3(image, 'appnewsposters', image_filename)
                if not resized_image_url['success']:
                    print(f"[ERROR] Image upload to AWS failed: {resized_image_url['error']}")
                    return {
                        'error': f'Image couldn\'t be uploaded to AWS: {resized_image_url["error"]}',
                        'articles_saved': articles_saved,
                        'unwanted_articles_saved': unwanted_articles_saved
                    }
            except Exception as e:
                print(f"[ERROR] Unexpected error while uploading image to AWS: {e}")
                return {
                    'error': 'Unexpected error while uploading image to AWS',
                    'articles_saved': articles_saved,
                    'unwanted_articles_saved': unwanted_articles_saved
                }

            # Save the article to the database
            new_article = Article(
                title=new_article_title,
                content=final_summary,
                image=image_filename,
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
            send_NEWS_message_to_slack_channel(channel_id=category_slack_channel, 
                                            title=new_article_title,
                                            article_url=news_link,
                                                content=final_summary, 
                                                used_keywords=used_keywords, 
                                                image=image_url)

            print(f"[SUCCESS] Article {new_article_title} validated and saved")
            return {
                'message': f'article {new_article_title} validated and saved',
                'articles_saved': articles_saved,
                'unwanted_articles_saved': unwanted_articles_saved
            }

    except Exception as e:
        print(f"[ERROR] An unexpected error occurred during keyword validation: {e}")
        return {
            'error': f"An unexpected error occurred during keyword validation: {e}",
            'articles_saved': articles_saved,
            'unwanted_articles_saved': unwanted_articles_saved
        }

def fetch_article_content(news_link: str, category_id: int, title: str, bot_id: int, bot_name: str, category_slack_channel) -> Dict[str, Any]:
    print(f"\n[INFO] Fetching article content for: {news_link}")
    
    try:
        # Send HTTP GET request
        response = requests.get(news_link, timeout=10)
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
            print(f"[ERROR] Content is not HTML for URL: {news_link}")
            return {'success': False, 'url': news_link, 'title': title, 
                    'paragraphs': [], 'error': "Content is not HTML"}

        html = BeautifulSoup(response.text, 'html.parser')

        # If the article is from Yahoo, validate the date
        if 'yahoo' in news_link.lower():
            if not validate_yahoo_date(html):
                print(f"[WARNING] Yahoo article is older than 24 hours: {news_link}")
                return {'success': False, 'url': news_link, 'title': title, 
                        'paragraphs': [], 'error': 'Yahoo article is older than 24 hours'}

        # Extract article title
        title_element = html.find('h1')
        article_title = title_element.text.strip() if title_element else title
        print(f"[INFO] Article title: {article_title}")

        # Extract paragraphs from the article
        paragraphs = html.find_all('p')
        article_content = [p.text.strip() for p in paragraphs if p.text.strip()]
        print(f"[INFO] Extracted {len(article_content)} paragraphs")

       
        
        publication_date = None
        date_elements = html.find_all(['span', 'date', 'time'])
        for date_element in date_elements:
            date_text = date_element.get('datetime') or date_element.text.strip()
            try:
                # Try to parse the date text
                publication_date = datetime.strptime(date_text, '%b %d, %Y at %I:%M %p')
                break  # Exit loop if date is successfully parsed
            except (ValueError, TypeError):
                try:
                    # Try another common date format
                    publication_date = datetime.strptime(date_text, '%Y-%m-%d')
                    break
                except (ValueError, TypeError):
                    continue  # Continue if parsing fails
        
        print(f"[INFO] Datetime: {publication_date}")
        # Check if the publication date is within the last 24 hours
        if publication_date and datetime.now() - publication_date > timedelta(days=1):
            print(f"[ERROR] datetime is older than 24h: {publication_date}")
            return {'success': False, 'url': news_link, 'title': article_title, 
                    'paragraphs': article_content, 'error': 'Article is older than 24 hours'}

        # Validate and process the content
        result = validate_and_save_article(news_link, article_title, article_content, 
                                           category_id, bot_id, bot_name, category_slack_channel)
         
        if 'error' in result:
            return {'success': False, 'url': news_link, 'title': article_title, 
                    'paragraphs': article_content, 'error': result['error']}

        print(f"[SUCCESS] {result['message']}")
        return {'success': True, 'url': news_link, 'title': article_title, 
                'paragraphs': article_content, 'message': result['message']}

    except requests.RequestException as e:
        print(f"[ERROR] Request error for {news_link}: {e}")
        return {'success': False, 'url': news_link, 'title': None, 
                'paragraphs': [], 'error': f"Request error: {e}"}
    except Exception as e:
        print(f"[ERROR] Unexpected error while processing {news_link}: {e}")
        return {'success': False, 'url': news_link, 'title': None, 
                'paragraphs': [], 'error': f'Error while getting article content: {str(e)}'}


