from datetime import datetime
from flask import Blueprint, jsonify, request
from config import Site, db

sites_bp = Blueprint(
    'sites_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Ruta para obtener todos los sites filtrados por bot_id
@sites_bp.route('/get_sites_by_bot', methods=['POST'])
def get_sites_by_bot():
    try:
        data = request.json
        bot_id = data.get('bot_id')

        if bot_id is None:
            return jsonify({'error': 'Bot ID missing in request data'}), 400

        sites = Site.query.filter_by(bot_id=bot_id).all()
        site_data = []
        for site in sites:
            site_data.append({
                'id': site.id,
                'name': site.name,
                'url': site.url,
                'bot_id': site.bot_id,
                'created_at': site.created_at,
                'updated_at': site.updated_at
            })
        return jsonify({'message': site_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Ruta para agregar un nuevo site
@sites_bp.route('/add_site', methods=['POST'])
def add_site():
    try:
        data = request.json
        new_site = Site(name=data['name'], url=data['url'], bot_id=data['bot_id'], created_at=datetime.now(), updated_at=datetime.now())
        db.session.add(new_site)
        db.session.commit()
        return jsonify({'message': 'Site added successfully', 'site_id': new_site.id}), 201
    except KeyError as e:
        return jsonify({'error': f'Missing key in request data: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
# Ruta para eliminar un site por ID
@sites_bp.route('/delete_site', methods=['DELETE'])
def delete_site():
    try:
        data = request.json
        site_id = data.get('site_id')

        if site_id is None:
            return jsonify({'error': 'Site ID missing in request data'}), 400

        site = Site.query.get(site_id)
        if site:
            db.session.delete(site)
            db.session.commit()
            return jsonify({'message': 'Site deleted successfully'}), 200
        else:
            return jsonify({'error': 'Site not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

