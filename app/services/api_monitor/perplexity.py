import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_perplexity_usage():
    """
    Retrieves API credit usage details from the Perplexity API.

    Returns:
        dict: A dictionary containing the usage details if successful, 
              or an error message if the request fails.
    """
    api_key = os.getenv('PERPLEXITY_API_KEY')
    if not api_key:
        return {"error": "API key not found in environment variables"}

    url = "https://api.perplexity.ai/v1/credits/usage"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()

        if response.headers.get('Content-Type') == 'application/json':
            return response.json()
        else:
            return {"error": "Unexpected content type"}
    except requests.exceptions.HTTPError as errh:
        return {"error": f"HTTP Error: {errh}"}
    except requests.exceptions.ConnectionError as errc:
        return {"error": f"Error Connecting: {errc}"}
    except requests.exceptions.Timeout as errt:
        return {"error": f"Timeout Error: {errt}"}
    except requests.exceptions.RequestException as err:
        return {"error": f"Request Error: {err}"}
    
    

uso_creditos = get_perplexity_usage()
print(uso_creditos)