from typing import Dict
from app.news_bot.utils import sanitize_filename
from app.services.d3.dalle3 import generate_poster_prompt, resize_and_upload_image_to_s3

def generate_and_upload_image(news_bot, article_summary: str) -> Dict:
    """
    Generates an image for the article summary and uploads it.
    """
    try:
        # Verificar si current_article_title está en blanco
        if not news_bot.current_article_title:
            raise ValueError("Current article title is empty or None")

        # Generar el prompt con el bot_id incluido
        prompt_result = generate_poster_prompt(article_summary, news_bot.bot_id)
        

        # Verificar si el prompt result es correcto
        if not prompt_result or 'response' not in prompt_result:
            raise ValueError("Failed to generate prompt or prompt is missing 'response'")

        image_url = prompt_result.get('response')
        if not image_url:
            raise ValueError("Image URL is None or empty")

        # Sanitize the article title to create a valid filename
        image_filename = f"{sanitize_filename(news_bot.current_article_title)}.png"
        bucket_name = "appnewsposters"
        upload_result = resize_and_upload_image_to_s3(image_url, bucket_name, image_filename)

        if not upload_result.get('success'):
            raise ValueError(f"Failed to upload image: {upload_result.get('error')}")

        return {'success': 'Image generated and uploaded successfully', 'image_url': upload_result.get('response')}
    
    except Exception as e:
        print("Error:", str(e))
        return {'error': f'Failed to generate or upload image: {str(e)}'}
