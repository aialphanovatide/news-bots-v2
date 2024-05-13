import os
import requests
from dotenv import load_dotenv 


# load_dotenv()
# PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

PERPLEXITY_API_KEY='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'

def perplexity_api_request(content, prompt, model='llama-3-sonar-large-32k-online'):
    url = "https://api.perplexity.ai/chat/completions"

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
                # print("Perplexity Content:", content_response) 
                return {'response': content_response, 'success': True}
            else:
                print("No 'message' key found in choices")
        else:
            print("No 'choices' key in the response or 'choices' is empty")

        return {'response': "No valid response found.", 'success': False}

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return {'response': str(e), 'success': False}
