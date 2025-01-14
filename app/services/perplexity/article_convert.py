from config import Bot
from .perplexity import perplexity_api_request


def article_perplexity_remaker(content, bot_id):
    try:
        if not content or not bot_id:
            return {'error': 'content and bot ID are required', 'success': False}
        
        final_content = f'In less than 4000 characters, please write an informative article referring to this content: {content}'
        
        bot = Bot.query.filter(Bot.id == bot_id).first()

        if not bot:
            return {'error': 'bot not found', 'success': False}
        
        bot_prompt = bot.prompt
        if not bot_prompt:
            return {'error': "Bot Prompt not found", 'success': False}
        
        bot_prompt_final = (
            bot_prompt +
            " Please ensure the following: 1) NEVER - don't include phrases like 'Here is a rewritten headline and summary of the article:', or Here is the rewritten headline and summary of the article:, or Here is the rewritten headline and summary of the article"
            "or similar at the start of the article. 2) The article should directly start with the content without any prefatory "
            "statements. 3) Maintain a professional tone appropriate for a knowledgeable audience."
        )
        
        perplexity_response = perplexity_api_request(final_content, bot_prompt_final)
        if perplexity_response['success']:
            return {'response': perplexity_response['response'], 'success': True}
        else:
            return {'error': f"Error at Perplexity: {perplexity_response['response']}", 'success': False}
    
    except Exception as e:
        return {'error': f"Error at: {str(e)}", 'success': False}
