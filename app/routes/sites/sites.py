from datetime import datetime
from flask import Blueprint, jsonify, request
from config import Site, db

sites_bp = Blueprint(
    'sites_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Get sites by bot ID
@sites_bp.route('/get_sites', methods=['GET'])
def get_sites_by_bot():
    response = {'data': None, 'error': None, 'success': False}
    try:
        bot_id = request.args.get('bot_id')

        if not bot_id:
            response['error'] = 'Bot ID is missing in the request data'
            return jsonify(response), 400

        sites = Site.query.filter_by(bot_id=bot_id).all()
        site_data = [site.as_dict() for site in sites]

        response['data'] = site_data
        response['success'] = True
        return jsonify(response), 200
    except Exception as e:
        response['error'] = f'Internal server error: {str(e)}'
        return jsonify(response), 500







# If we add a new site, then we have to modify the main logic as the index.py takes only one SITE_URL
# Ruta para agregar un nuevo site
# @sites_bp.route('/add_site', methods=['POST'])
# def add_site():
#     try:
#         data = request.json
#         new_site = Site(name=data['name'], url=data['url'], bot_id=data['bot_id'], created_at=datetime.now(), updated_at=datetime.now())
#         db.session.add(new_site)
#         db.session.commit()
#         return jsonify({'message': 'Site added successfully', 'site_id': new_site.id}), 201
#     except KeyError as e:
#         return jsonify({'error': f'Missing key in request data: {str(e)}'}), 400
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    



# If we let the users delete the site, then the main function won't work 
# # Ruta para eliminar un site por ID
# @sites_bp.route('/delete_site', methods=['DELETE'])
# def delete_site():
#     try:
#         data = request.json
#         site_id = data.get('site_id')

#         if site_id is None:
#             return jsonify({'error': 'Site ID missing in request data'}), 400

#         site = Site.query.get(site_id)
#         if site:
#             db.session.delete(site)
#             db.session.commit()
#             return jsonify({'message': 'Site deleted successfully'}), 200
#         else:
#             return jsonify({'error': 'Site not found'}), 404
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

