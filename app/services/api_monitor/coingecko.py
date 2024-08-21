import os
import requests
from dotenv import load_dotenv

load_dotenv()

COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

def get_coingecko_usage():
    """
    Retrieves API usage details from the CoinGecko Pro API.

    Args:
        api_key (str): Your CoinGecko Pro API key.

    Returns:
        dict: A dictionary containing the usage details if successful, 
              or an error message if the request fails.
    """
    url = "https://pro-api.coingecko.com/api/v3/key"
    headers = {
        "accept": "application/json",
        "x-cg-pro-api-key": COINGECKO_API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        return {"data": response.json()}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request exception: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}
    