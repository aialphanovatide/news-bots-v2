
# FILE DEPRACATED, SCHEDULE TO REMOVE AND DELETE AFTER PR https://github.com/aialphanovatide/ai-alpha-backend/pull/109 IS APPROVED


from flask import Blueprint, jsonify
from app.routes.routes_utils import create_response
from app.services.api_monitor.coingecko import get_coingecko_usage


coingecko_bp = Blueprint('coingecko_bp', __name__)


@coingecko_bp.route('/coingecko/usage', methods=['GET'])
def get_coingecko_usage_endpoint():
    """
    Retrieve the API usage details from the CoinGecko Pro API.
    """
    try:
        usage_details = get_coingecko_usage()
        if 'error' in usage_details:
            return jsonify(create_response(success=False, error=usage_details['error'])), 500
        return jsonify(create_response(success=True, data=usage_details['data']))
    except Exception as e:
        return jsonify(create_response(success=False, error=str(e))), 500

