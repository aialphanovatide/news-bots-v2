from datetime import datetime
from flask import Blueprint, jsonify, request
from app.utils.helpers import measure_execution_time
from config import Site, db
from sqlalchemy.exc import SQLAlchemyError
from app.routes.routes_utils import create_response, handle_db_session

sites_bp = Blueprint(
    'sites_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# FILE DEPRACATED, SCHEDULE TO REMOVE AND DELETE AFTER SERVER UPDATE


@sites_bp.route('/get_sites', methods=['GET'])
@measure_execution_time
@handle_db_session
def get_sites_by_bot():
    """
    Retrieve sites associated with a bot specified by bot_id.
    Args:
        bot_id (str): ID of the bot to retrieve sites for.
    Response:
        200: Successful response with site data.
        400: Missing bot ID in request parameters.
        500: Internal server error or database error.
    """
    try:
        bot_id = request.args.get('bot_id')

        if not bot_id:
            response = create_response(error='Bot ID is missing in the request data')
            return jsonify(response), 400

        sites = Site.query.filter_by(bot_id=bot_id).all()
        site_data = [site.as_dict() for site in sites]

        response = create_response(success=True, data=site_data)
        return jsonify(response), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@sites_bp.route('/add_site', methods=['POST'])
@measure_execution_time
@handle_db_session
def add_site():
    """
    Add a new site associated with a bot.
    Data:
        JSON data with 'name' (str), 'url' (str), and 'bot_id' (int).
    Response:
        201: Site added successfully with site_id in response.
        400: Missing key in request data.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        new_site = Site(name=data['name'], url=data['url'], bot_id=data['bot_id'], created_at=datetime.now(), updated_at=datetime.now())
        db.session.add(new_site)
        db.session.commit()
        response = create_response(success=True, message='Site added successfully', site_id=new_site.id)
        return jsonify(response), 201

    except KeyError as e:
        response = create_response(error=f'Missing key in request data: {str(e)}')
        return jsonify(response), 400

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500


@sites_bp.route('/delete_site', methods=['DELETE'])
@measure_execution_time
@handle_db_session
def delete_site():
    """
    Delete a site by ID associated with a bot.
    Data:
        JSON data with 'site_id' (int).
    Response:
        200: Site deleted successfully.
        400: Site ID missing in request data.
        404: Site not found.
        500: Internal server error or database error.
    """
    try:
        data = request.json
        site_id = data.get('site_id')

        if site_id is None:
            response = create_response(error='Site ID missing in request data')
            return jsonify(response), 400

        site = Site.query.get(site_id)
        if site:
            db.session.delete(site)
            db.session.commit()
            response = create_response(success=True, message='Site deleted successfully')
            return jsonify(response), 200
        else:
            response = create_response(error='Site not found')
            return jsonify(response), 404

    except SQLAlchemyError as e:
        db.session.rollback()
        response = create_response(error=f'Database error: {str(e)}')
        return jsonify(response), 500

    except Exception as e:
        response = create_response(error=f'Internal server error: {str(e)}')
        return jsonify(response), 500
