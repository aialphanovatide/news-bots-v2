
# FILE DEPRACATED, SCHEDULE TO REMOVE AND DELETE AFTER PR https://github.com/aialphanovatide/ai-alpha-backend/pull/109 IS APPROVED


import os
from flask import Blueprint, jsonify
import requests
from app.routes.routes_utils import create_response
from app.services.api_monitor.coingecko import get_coingecko_usage
from dotenv import load_dotenv

load_dotenv()

COINGECKO_API_KEY = os.getenv('COINGECKO_APIKEY')

coingecko_bp = Blueprint('coingecko_bp', __name__)


@coingecko_bp.route('/api/v1/coingecko/usage', methods=['GET'])
def coingecko_usage():
    """
    Retrieve CoinGecko API usage information.
    """
    api_key = COINGECKO_API_KEY
    url = 'https://pro-api.coingecko.com/api/v3/key'
    headers = {'X-Cg-Pro-Api-Key': api_key}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(create_response(success=True, data=response.json())), 200
    except requests.RequestException as e:
        error_message = f"Error fetching CoinGecko API usage: {e}"
        if e.response is not None:
            error_message += f" Response: {e.response.text}"
        return jsonify(create_response(success=False, error=error_message)), 500