import os
import requests
from dotenv import load_dotenv 


load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

def perplexity_api_request(content, prompt="Be precise and concise", model='codellama-70b-instruct'):
    
    url = "https://api.perplexity.ai/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
       
        response.raise_for_status()  

        choices = response.json().get('choices', [])
        if choices:
            assistant_message = choices[0].get('message', {})
            answer_content = assistant_message.get('content', None)
            
            if answer_content:
                return {'response': answer_content, 'success': True}
            else:
                print(f"No answer found for this prompt: {prompt}. Error: {assistant_message}")
                return {'response': f"No answer found for this prompt: {prompt}. Error: {assistant_message}", 'success': False}
        else:
            print(f"No choices found for this prompt: {prompt} - in the API response.")
            return {'response': f"No choices found for this prompt: {prompt}, Error: {choices}", 'success': False}
    
    except requests.exceptions.RequestException as err:
        print(f"Error during API request: {err}")
        return {'response': f"Error during API request: {err}", 'success': False}
    