from config import Category
from .perplexity import perplexity_api_request


def article_perplexity_remaker(content, category_id):
    try:
        if not content or not category_id:
            return {'error': 'content and category ID are required', 'success': False}
        
        final_content = f'In less than 1800 characters, please write an infomative article refered to this content: {content}'
        
        category = Category.query.filter(Category.id == category_id).first()

        if not category:
            return {'error': 'category not found', 'success': False}
        
        bot_prompt = category.prompt
        if not bot_prompt:
            return {'error': "Bot Prompt not found", 'success': False}
        
        perplexity_response = perplexity_api_request(final_content, bot_prompt)
        if perplexity_response['success']:
            return {'response': perplexity_response['response'], 'success': True}
        else:
            return {'error': f"Error at Perplexity: {perplexity_response['response']}", 'success': False}
    
    except Exception as e:
        return {'error': f"Error at: {str(e)}", 'success': False}

    