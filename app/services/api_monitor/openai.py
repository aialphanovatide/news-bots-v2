import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


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



# ____________________ Working version by David 21/08/2024 _________________________



def group_data(data, prices):
    usage_by_snapshot = {}

    if "data" in data:
        for item in data["data"]:
            snapshot_id = item["snapshot_id"]
            if snapshot_id not in usage_by_snapshot:
                usage_by_snapshot[snapshot_id] = {
                    "operation": item["operation"],
                    "n_requests": 0,
                    "n_context_tokens_total": 0,
                    "n_generated_tokens_total": 0,
                    "cost_context_plus_generated": 0
                }

            usage_by_snapshot[snapshot_id]["n_requests"] += item["n_requests"]
            usage_by_snapshot[snapshot_id]["n_context_tokens_total"] += item["n_context_tokens_total"]
            usage_by_snapshot[snapshot_id]["n_generated_tokens_total"] += item["n_generated_tokens_total"]


    if "dalle_api_data" in data:
        for item in data["dalle_api_data"]:
            model_id = item["model_id"]
            if model_id not in usage_by_snapshot:
                usage_by_snapshot[model_id] = {
                    "operation": item["operation"],
                    "num_requests": 0,
                    "num_images": 0,
                    "cost": 0
                }
            
            usage_by_snapshot[model_id]["num_requests"] += item["num_requests"]
            usage_by_snapshot[model_id]["num_images"] += item["num_images"]


    return usage_by_snapshot

def openai_usage_endpoint(days_ago=30):
    url = "https://api.openai.com/v1/usage"
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_ago)
    
    params = {
        "date": end_date.isoformat()
    }
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # Define cost per token/image for each model
    prices = {
        "gpt-4o-2024-05-13_input": 0.005,  # per 1K tokens
        "gpt-4o-2024-05-13_output": 0.015,  # per 1K tokens
        "gpt-4-0613_input": 0.03,  # per 1K tokens
        "gpt-4-0613_output": 0.06,  # per 1K tokens
        "text-embedding-ada-002-v2": 0.0001,  # per 1K tokens
        "dall-e-3": 0.080  # per image
    }
   
    try:
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            usage_data = response.json()
            grouped_data = group_data(usage_data, prices)

            # Uncomment when you want to see the raw data from OpenAI
            # with open("openai-usage-raw.json", "w") as f:
            #     json.dump(usage_data, f, indent=2)
            # print("API request successful. Grouped usage data saved to openai-usage.json")
            
            return grouped_data
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Error message: {response.text}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


