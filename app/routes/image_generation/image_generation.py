from flask import Blueprint, request, jsonify
from app.news_bot.news_bot_v2.image_generator import ImageGenerator, ImageConfig
from http import HTTPStatus

image_generation_bp = Blueprint('image_generation', __name__)

@image_generation_bp.route('/generate-image', methods=['POST'])
def generate_dalle_image():
    """
    Generate an image using DALL-E based on the provided prompt and style settings.
    
    Expected JSON payload:
    {
        "prompt": "string",
        "style": "natural" | "vivid" (optional),
        "quality": "standard" | "hd" (optional)
    }

    Returns:
        JSON response with image URL or error message
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No JSON data provided'
            }), HTTPStatus.BAD_REQUEST
        
        if 'prompt' not in data:
            return jsonify({
                'error': 'Missing required field: prompt'
            }), HTTPStatus.BAD_REQUEST

        # Create custom config if style parameters are provided
        config_params = {}
        if 'style' in data:
            if data['style'] not in ['natural', 'vivid']:
                return jsonify({
                    'error': 'Invalid style value. Must be either "natural" or "vivid"'
                }), HTTPStatus.BAD_REQUEST
            config_params['image_style'] = data['style']

        if 'quality' in data:
            if data['quality'] not in ['standard', 'hd']:
                return jsonify({
                    'error': 'Invalid quality value. Must be either "standard" or "hd"'
                }), HTTPStatus.BAD_REQUEST
            config_params['image_quality'] = data['quality']

        # Initialize ImageGenerator with custom config if provided
        config = ImageConfig(**config_params) if config_params else None
        image_generator = ImageGenerator(config=config)

        # Generate the image
        image_url = image_generator._generate_dalle_image(
            prompt=data['prompt']
        )

        return jsonify({
            'success': True,
            'image_url': image_url,
            'settings': {
                'style': config.image_style if config else 'natural',
                'quality': config.image_quality if config else 'hd'
            }
        }), HTTPStatus.OK

    except ValueError as e:
        return jsonify({
            'error': str(e),
            'error_type': 'validation_error'
        }), HTTPStatus.BAD_REQUEST

    except Exception as e:
        return jsonify({
            'error': 'An unexpected error occurred',
            'error_type': 'server_error'
        }), HTTPStatus.INTERNAL_SERVER_ERROR