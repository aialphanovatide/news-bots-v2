import os
import requests
from dotenv import load_dotenv 


load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")


def perplexity_api_request(content, prompt, model='llama-3-sonar-large-32k-online'):
    url = "https://api.perplexity.ai/chat/completions"

    if not content or not prompt:
        return {'response': 'content and prompt are required', 'success': False}

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()  # Convierte la respuesta en JSON

        if response_data.get('choices'):
            first_choice = response_data['choices'][0]
            if 'message' in first_choice:
                content_response = first_choice['message']['content']
                return {'response': content_response, 'success': True}
            else:
                return {'response': "No 'message' key found in choices", 'success': False}

        else:
            return {'response': "No 'choices' key in the response or 'choices' is empty", 'success': False}

    except requests.exceptions.RequestException as e:
        return {'response': f'Perplexity API request failed: {str(e)}', 'success': False}
    
    except Exception as e:
        return {'response': f'Perplexity failed: {str(e)}', 'success': False}
    

# Example usage
# Prompt = 'Be precise and concise'
# content = 'What is a matrix?'
# print(perplexity_api_request(content=content, prompt=Prompt))
