from config import Category
import asyncio

from .utils import perplexity_api_request

def article_perplexity_remaker(content, category_id):
    try:
        category = Category.query.filter(Category.id == category_id).first()
        if category:
            bot_prompt = category.prompt
        final_content = f'In less than 1800 characters, please write an infomative article refered to this content: {content}'
        perplexity_response = perplexity_api_request(final_content, bot_prompt)
        if perplexity_response['success']:
            return perplexity_response['response']
        else:
            return f"Error at Perplexity: {perplexity_response['response']}"
    except Exception as e:
        return f"Error at: {str(e)}"

    