# Importa las librerías necesarias
import os
from flask import Blueprint, jsonify
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session
from app.services.api_monitor.coingecko import get_coingecko_usage
from dotenv import load_dotenv
load_dotenv()

coingeko_bp = Blueprint('coingeko_bp', __name__)

@coingeko_bp.route('/api/cg-usage', methods=['GET'])
@handle_db_session
def get_usage():
    """
    Retrieve API usage details from CoinGecko.
    Response:
        200: Usage details retrieved successfully.
        500: Internal server error.
    """
    try:
        api_key = os.getenv('COINGECKO_APIKEY')
        usage_data = get_coingecko_usage(api_key)
        
        if 'error' in usage_data:
            response = create_response(error=usage_data['error'])
            return jsonify(response), 500
        
        response = create_response(success=True, data=usage_data)
        return jsonify(response), 200
        
    except SQLAlchemyError as e:
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500
    except Exception as e:
        response = create_response(error=f'Error retrieving API usage: {str(e)}')
        return jsonify(response), 500
