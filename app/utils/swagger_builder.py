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
# swagger.add_or_update_endpoint(
#     endpoint_route='/bot',
#     method='post',
#     tag='Bots',
#     description='Create a new bot',
#     detail_description='''
#     Create a new bot with associated site, keywords, and blacklist.
    
#     The endpoint performs the following operations:
#     - Validates all required fields
#     - Checks for duplicate bot names
#     - Validates category existence
#     - Creates bot with normalized icon name
#     - Creates associated site if URL is provided
#     - Adds keywords (whitelist) if provided
#     - Adds blacklist entries if provided
#     - Handles all database operations with rollback capability
    
#     Note: The run_frequency must be at least 20 minutes, and URLs must contain 'news'/'google' and 'rss'.
#     ''',
#     params=[
#         {
#             'name': 'body',
#             'in': 'body',
#             'description': 'Bot creation data',
#             'required': True,
#             'schema': {
#                 'type': 'object',
#                 'required': ['name', 'alias', 'category_id', 'run_frequency'],
#                 'properties': {
#                     'name': {
#                         'type': 'string',
#                         'description': 'Unique name for the bot'
#                     },
#                     'alias': {
#                         'type': 'string',
#                         'description': 'Display name for the bot'
#                     },
#                     'category_id': {
#                         'type': 'integer',
#                         'description': 'ID of the category the bot belongs to'
#                     },
#                     'dalle_prompt': {
#                         'type': 'string',
#                         'description': 'DALL-E prompt for bot image generation',
#                         'required': False
#                     },
#                     'background_color': {
#                         'type': 'string',
#                         'description': 'HEX color code for bot background',
#                         'required': False,
#                         'example': '#4287f5'
#                     },
#                     'run_frequency': {
#                         'type': 'integer',
#                         'description': 'Bot execution frequency in minutes (minimum 20)',
#                         'minimum': 20
#                     },
#                     'url': {
#                         'type': 'string',
#                         'description': 'RSS feed URL (must contain news/google and rss)',
#                         'required': False,
#                         'example': 'https://rss.news.google.com/search?q=tech%20news'
#                     },
#                     'whitelist': {
#                         'type': 'string',
#                         'description': 'Comma-separated list of keywords to match',
#                         'required': False,
#                         'example': 'AI, machine learning, robotics'
#                     },
#                     'blacklist': {
#                         'type': 'string',
#                         'description': 'Comma-separated list of words to filter out',
#                         'required': False,
#                         'example': 'spam, scam, adult content'
#                     }
#                 }
#             }
#         }
#     ],
#     responses={
#         '201': {
#             'description': 'Bot created successfully',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'bot': {
#                         'type': 'object',
#                         'properties': {
#                             'id': {'type': 'integer'},
#                             'name': {'type': 'string'},
#                             'alias': {'type': 'string'},
#                             'category_id': {'type': 'integer'},
#                             'dalle_prompt': {'type': 'string'},
#                             'prompt': {'type': 'string'},
#                             'icon': {'type': 'string'},
#                             'background_color': {'type': 'string'},
#                             'run_frequency': {'type': 'integer'},
#                             'is_active': {'type': 'boolean'},
#                             'created_at': {'type': 'string', 'format': 'date-time'},
#                             'updated_at': {'type': 'string', 'format': 'date-time'}
#                         }
#                     },
#                     'message': {'type': 'string'}
#                 }
#             }
#         },
#         '400': {
#             'description': 'Bad request',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {
#                         'type': 'string',
#                         'description': 'Error message detailing the validation failure',
#                         'examples': [
#                             'Missing field in request data: name',
#                             'Run frequency must be an integer of at least 20 minutes',
#                             'A bot with the name \'Test Bot\' already exists',
#                             'Invalid URL provided',
#                             'Whitelist must be a comma-separated string'
#                         ]
#                     }
#                 }
#             }
#         },
#         '404': {
#             'description': 'Category not found',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {'type': 'string'}
#                 }
#             }
#         },
#         '500': {
#             'description': 'Internal server error',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {
#                         'type': 'string',
#                         'description': 'Error message from the server',
#                         'examples': [
#                             'Database error: [SQL error details]',
#                             'An unexpected error occurred: [error details]'
#                         ]
#                     }
#                 }
#             }
#         }
#     }
# )

# # ____Delete an endpoint____
# success, message = swagger.delete_endpoint(endpoint_route='/articles/unwanted')
# print(message)


