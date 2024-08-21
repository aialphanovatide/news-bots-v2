import requests

def get_coingecko_usage(api_key):
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
        "x-cg-pro-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}