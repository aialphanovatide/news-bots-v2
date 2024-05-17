from flask import Blueprint, jsonify
from config import Category
import requests
from config import db
from flask import request


categories_bp = Blueprint(
    'categories_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@categories_bp.route('/add_new_category', methods=['POST'])
def create_category():
    try:
        # Obtener datos del cuerpo de la petición
        data = request.get_json()
        
        # Validar los datos recibidos (este es un ejemplo, debes adaptar las validaciones a tus necesidades)
        if 'name' not in data or 'alias' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Crear la instancia de la categoría
        new_category = Category(
            name=data['name'],
            alias=data['alias'],
            prompt=data.get('prompt', ''),
            time_interval=data.get('time_interval', None),
            is_active=data.get('is_active', True),
            border_color=data.get('border_color', None),
            icon=data.get('icon', None)
        )
        
        # Guardar la nueva categoría en la base de datos
        db.session.add(new_category)
        db.session.commit()
        
        # Devolver una respuesta con la categoría creada
        return jsonify({
            'id': new_category.id,
            'name': new_category.name,
            'alias': new_category.alias,
            'prompt': new_category.prompt,
            'time_interval': new_category.time_interval,
            'is_active': new_category.is_active,
            'border_color': new_category.border_color,
            'icon': new_category.icon
        }), 201

    except Exception as e:
        # Manejar excepciones generales
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

    

@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        category_data = []
        for category in categories:
            category_data.append({
                'id': category.id,
                'name': category.name,
                'alias': category.alias,
                'prompt': category.prompt,
                'time_interval': category.time_interval,
                'is_active': category.is_active,
                'border_color': category.border_color,
                'icon': category.icon,
            })
        return jsonify({'message': category_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
