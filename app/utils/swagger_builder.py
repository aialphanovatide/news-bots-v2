# Helper function to updated the Swagger JSON file

import os
import json
from typing import Tuple

class Swagger:
    def __init__(self):
        self.path = os.path.join('app','static', 'swagger.json')

    def load(self) -> dict:
        """
        Load and parse the Swagger JSON file.

        Returns:
            dict: The parsed Swagger JSON data.

        Raises:
            FileNotFoundError: If the Swagger file is not found at the specified path.
            json.JSONDecodeError: If the Swagger file contains invalid JSON.
            Exception: For any other unexpected errors during file loading.
        """
        try:
            with open(self.path, 'r') as file:
                self.swagger_json = json.load(file)
            return self.swagger_json
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: Swagger file not found at {self.path}")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(f"Error: Invalid JSON in Swagger file at {self.path}")
        except Exception as e:
            raise Exception(f"Unexpected error loading Swagger file: {str(e)}")

    def add_or_update_endpoint(self, endpoint_route: str, method: str, tag: str, description: str, detail_description: str, params: list, responses: dict) -> Tuple[bool, str]:
        """
        Add a new endpoint to the Swagger JSON file or update an existing one
        """
        try:
            # Open the Swagger JSON file
            swagger_json = self.load()
            if swagger_json is None:
                return False, "Failed to load Swagger JSON file"

            # Check if the endpoint already exists
            endpoint_exists = endpoint_route in swagger_json['paths'] and method in swagger_json['paths'][endpoint_route]
            
            if endpoint_exists:
                print(f'Endpoint {endpoint_route} [{method}] already exists. Updating...')
            else:
                print(f'Adding new endpoint {endpoint_route} [{method}]...')

            # Create or update the endpoint
            if endpoint_route not in swagger_json['paths']:
                swagger_json['paths'][endpoint_route] = {}
            
            # Add or update the endpoint with its details
            swagger_json['paths'][endpoint_route][method] = {
                'tags': [tag.capitalize()],
                'summary': description.capitalize(),
                'description': detail_description.capitalize(),
                'parameters': [],
                'responses': responses
            }
            
            # Add parameters if they exist
            try:
                for param in params:
                    parameter = {
                        'name': param.get('name', ''),
                        'in': param.get('in', 'query'),
                        'description': param.get('description', ''),
                        'required': param.get('required', False),
                        'type': param.get('type', 'string'),  # Default to string if type is missing
                        'schema': param.get('schema', {})  # Use an empty dict as fallback
                    }
                    # Only append valid parameters
                    if parameter['name']:
                        swagger_json['paths'][endpoint_route][method]['parameters'].append(parameter)
            except Exception as e:
                return False, f'Error processing parameters: {str(e)}'

            # Update the Swagger JSON file
            with open(self.path, 'w') as file:
                json.dump(swagger_json, file, indent=2)

            action = "updated" if endpoint_exists else "added"
            return True, f'Endpoint {endpoint_route} [{method}] {action} successfully'
        except Exception as e:
            return False, f'Error adding/updating endpoint {endpoint_route} [{method}]: {str(e)}'

    def delete_endpoint(self, endpoint_route: str) -> Tuple[bool, str]:
        """
        Delete an endpoint from the Swagger JSON file
        """
        try:
            swagger_path = self.path
            
            # Check if the Swagger JSON file exists
            if not os.path.exists(swagger_path):
                return False, "Swagger JSON file not found"

            # Load the Swagger JSON file
            with open(swagger_path, 'r') as file:
                swagger_json = json.load(file)

            # Check if the endpoint exists
            if endpoint_route not in swagger_json.get('paths', {}):
                return False, f"Endpoint {endpoint_route} not found"

            # Delete the endpoint
            del swagger_json['paths'][endpoint_route]

            # Write the updated Swagger JSON back to the file
            with open(swagger_path, 'w') as file:
                json.dump(swagger_json, file, indent=2)

            return True, f"Endpoint {endpoint_route} deleted successfully"

        except Exception as e:
            return False, f"Error deleting endpoint {endpoint_route}: {str(e)}"
 


# Example usage
swagger = Swagger()

# ____Add or update an endpoint____

swagger = Swagger()

# swagger.add_or_update_endpoint(
#     endpoint_route='/generate-image',
#     method='post',
#     tag='Image Generation',
#     description='Generate an image using DALL-E based on the provided prompt',
#     detail_description='''
#     Generate an AI image using DALL-E 3 with customizable settings.
    
#     Features:
#     - Supports both natural and vivid image styles
#     - Configurable image quality (standard or HD)
#     - Default settings: natural style, HD quality
#     - Returns direct URL to the generated image
    
#     Example request body:
#     {
#         "prompt": "A serene mountain landscape at sunset",
#         "style": "vivid",
#         "quality": "hd"
#     }
#     ''',
#     params=[
#         {
#             'name': 'body',
#             'in': 'body',
#             'description': 'Image generation parameters',
#             'required': True,
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'prompt': {
#                         'type': 'string',
#                         'description': 'The image generation prompt',
#                         'example': 'A serene mountain landscape at sunset'
#                     },
#                     'style': {
#                         'type': 'string',
#                         'description': 'Image style preference',
#                         'enum': ['natural', 'vivid'],
#                         'default': 'natural'
#                     },
#                     'quality': {
#                         'type': 'string',
#                         'description': 'Image quality setting',
#                         'enum': ['standard', 'hd'],
#                         'default': 'hd'
#                     }
#                 },
#                 'required': ['prompt']
#             }
#         }
#     ],
#     responses={
#         '200': {
#             'description': 'Successfully generated image',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {
#                         'type': 'boolean',
#                         'example': True
#                     },
#                     'image_url': {
#                         'type': 'string',
#                         'description': 'URL of the generated image',
#                         'example': 'https://oaidalleapiprodscus.blob.core.windows.net/private/...'
#                     },
#                     'settings': {
#                         'type': 'object',
#                         'properties': {
#                             'style': {
#                                 'type': 'string',
#                                 'description': 'Style used for generation',
#                                 'example': 'natural'
#                             },
#                             'quality': {
#                                 'type': 'string',
#                                 'description': 'Quality setting used',
#                                 'example': 'hd'
#                             }
#                         }
#                     }
#                 }
#             }
#         },
#         '400': {
#             'description': 'Bad request',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'error': {
#                         'type': 'string',
#                         'examples': [
#                             'No JSON data provided',
#                             'Missing required field: prompt',
#                             'Invalid style value. Must be either "natural" or "vivid"',
#                             'Invalid quality value. Must be either "standard" or "hd"'
#                         ]
#                     },
#                     'error_type': {
#                         'type': 'string',
#                         'example': 'validation_error'
#                     }
#                 }
#             }
#         },
#         '500': {
#             'description': 'Internal server error',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'error': {
#                         'type': 'string',
#                         'example': 'An unexpected error occurred'
#                     },
#                     'error_type': {
#                         'type': 'string',
#                         'example': 'server_error'
#                     }
#                 }
#             }
#         }
#     }
# )

# ____Delete an endpoint____
# success, message = swagger.delete_endpoint(endpoint_route='/generate-dalle')
# print(message)


