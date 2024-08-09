import requests
import datetime
import time

def get_openai_usage(api_key):
    """
    Calculates the total token usage and cost for GPT-4 and image generation usage and cost for DALL-E 3
    from the start of the current month to today.

    Args:
        api_key (str): Your OpenAI API key.

    Returns:
        dict: A dictionary containing total tokens and costs for GPT-4 and DALL-E 3, or an error message if the request fails.
    """
    headers = {'Authorization': f'Bearer {api_key}'}
    url = 'https://api.openai.com/v1/usage'

    today = datetime.date.today()
    start_date = today.replace(day=1)

    total_context_tokens_gpt4 = 0
    total_generated_tokens_gpt4 = 0
    total_images_dalle3 = 0

    cost_per_generated_token_gpt4 = 0.03 / 1000
    cost_per_context_token_gpt4 = 0.01 / 1000
    cost_per_image_dalle3 = 0.02

    current_date = start_date
    retry_attempts = 5

    while current_date <= today:
        params = {'date': current_date.strftime('%Y-%m-%d')}
        
        for attempt in range(retry_attempts):
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()  # Raise an error for bad responses
                response_data = response.json()
                
                if 'data' in response_data:
                    for data in response_data['data']:
                        if data.get('snapshot_id') == 'gpt-4-0613':
                            total_context_tokens_gpt4 += data.get('n_context_tokens_total', 0)
                            total_generated_tokens_gpt4 += data.get('n_generated_tokens_total', 0)
                
                if 'dalle_api_data' in response_data:
                    for data in response_data['dalle_api_data']:
                        if data.get('model_id') == 'dall-e-3':
                            total_images_dalle3 += data.get('num_images', 0)
                
                break  # Exit the retry loop if the request was successful
            
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                elif response.status_code == 400:
                    return {"error": "Bad request, possibly invalid parameters."}
                else:
                    return {"error": str(e)}
            except requests.exceptions.RequestException as e:
                return {"error": str(e)}
        
        current_date += datetime.timedelta(days=1)

    total_cost_generated_gpt4 = total_generated_tokens_gpt4 * cost_per_generated_token_gpt4
    total_cost_context_gpt4 = total_context_tokens_gpt4 * cost_per_context_token_gpt4
    total_cost_gpt4 = total_cost_generated_gpt4 + total_cost_context_gpt4

    total_cost_dalle3 = total_images_dalle3 * cost_per_image_dalle3

    return {
        "total_tokens_gpt4": total_context_tokens_gpt4 + total_generated_tokens_gpt4,
        "total_cost_gpt4": total_cost_gpt4,
        "total_images_dalle3": total_images_dalle3,
        "total_cost_dalle3": total_cost_dalle3
    }
