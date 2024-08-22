import os
import requests
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

def get_perplexity_api_usage():
    """
    Retrieves API credit usage details from the Perplexity API.

    Returns:
        dict: A dictionary containing the usage details if successful, 
              or an error message if the request fails.
    """

    url = "https://api.perplexity.ai/v1/credits/usage"
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        if response.headers.get('Content-Type') == 'application/json':
            return {"data": response.json()}
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
    
    
