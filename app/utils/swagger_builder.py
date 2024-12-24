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
#     endpoint_route='/articles',
#     method='get',
#     tag='Articles',
#     description='Get all articles with advanced filtering and pagination',
#     detail_description='''
#     Retrieve articles with advanced filtering options including bot name, category name, 
#     top stories status, timeframes, and article type (valid/bin).
#     Results are ordered by creation date (most recent first).
#     ''',
#     params=[
#         {
#             'name': 'page',
#             'in': 'query',
#             'description': 'Page number for pagination',
#             'type': 'integer',
#             'default': 1
#         },
#         {
#             'name': 'per_page',
#             'in': 'query',
#             'description': 'Number of items per page',
#             'type': 'integer',
#             'default': 10
#         },
#         {
#             'name': 'search',
#             'in': 'query',
#             'description': 'Search term to filter articles by content or title',
#             'type': 'string'
#         },
#         {
#             'name': 'bot_name',
#             'in': 'query',
#             'description': 'Filter articles by bot name',
#             'type': 'string'
#         },
#         {
#             'name': 'category_name',
#             'in': 'query',
#             'description': 'Filter articles by category name',
#             'type': 'string'
#         },
#         {
#             'name': 'top_stories',
#             'in': 'query',
#             'description': 'If "true", return only top stories',
#             'type': 'boolean'
#         },
#         {
#             'name': 'timeframe',
#             'in': 'query',
#             'description': 'Filter top stories by timeframe',
#             'type': 'string',
#             'enum': ['1D', '1W', '1M']
#         },
#         {
#             'name': 'bin',
#             'in': 'query',
#             'description': 'If "true", include unwanted articles',
#             'type': 'boolean',
#             'default': False
#         },
#         {
#             'name': 'valid_articles',
#             'in': 'query',
#             'description': 'If "true", include valid articles',
#             'type': 'boolean',
#             'default': True
#         }
#     ],
#     responses={
#         '200': {
#             'description': 'Successfully retrieved articles',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {
#                         'type': 'boolean',
#                         'example': True
#                     },
#                     'data': {
#                         'type': 'array',
#                         'items': {
#                             'type': 'object',
#                             'properties': {
#                                 'id': {'type': 'integer'},
#                                 'title': {'type': 'string'},
#                                 'content': {'type': 'string'},
#                                 'image': {'type': 'string'},
#                                 'url': {'type': 'string'},
#                                 'date': {'type': 'string', 'format': 'date-time'},
#                                 'bot_id': {'type': 'integer'},
#                                 'created_at': {'type': 'string', 'format': 'date-time'},
#                                 'updated_at': {'type': 'string', 'format': 'date-time'},
#                                 'is_top_story': {'type': 'boolean'},
#                                 'type': {'type': 'string', 'enum': ['valid', 'bin']}
#                             }
#                         }
#                     },
#                     'pagination': {
#                         'type': 'object',
#                         'properties': {
#                             'page': {'type': 'integer'},
#                             'per_page': {'type': 'integer'},
#                             'total_pages': {'type': 'integer'},
#                             'total_items': {'type': 'integer'}
#                         }
#                     },
#                     'filters': {
#                         'type': 'object',
#                         'properties': {
#                             'bot_name': {'type': 'string'},
#                             'category_name': {'type': 'string'},
#                             'timeframe': {'type': 'string'}
#                         }
#                     }
#                 }
#             }
#         },
#         '204': {
#             'description': 'No articles found',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean', 'example': True},
#                     'data': {'type': 'array', 'items': {}},
#                     'message': {'type': 'string', 'example': 'No articles found'}
#                 }
#             }
#         },
#         '400': {
#             'description': 'Bad request',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean', 'example': False},
#                     'error': {
#                         'type': 'string',
#                         'examples': [
#                             'Page and per_page must be positive integers',
#                             'At least one article type must be selected',
#                             'Invalid timeframe: 2D. Must be one of: 1D, 1W, 1M'
#                         ]
#                     }
#                 }
#             }
#         },
#         '500': {
#             'description': 'Internal server error',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean', 'example': False},
#                     'error': {'type': 'string', 'example': 'An unexpected error occurred: Database error'}
#                 }
#             }
#         }
#     }
# )

# ____Delete an endpoint____
# success, message = swagger.delete_endpoint(endpoint_route='/articles/all')
# print(message)


