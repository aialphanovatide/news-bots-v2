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
#     endpoint_route='/top-stories',
#     method='get',
#     tag='Top Stories',
#     description='Get paginated top stories with optional filtering',
#     detail_description='''
#     Retrieve top stories from the database with optional filtering and pagination support.
    
#     Features:
#     - Results are ordered by date (most recent first)
#     - Stories are grouped by bot_id in the response
#     - Default pagination: 10 items per page, starting at page 1
#     - Optional filtering by timeframe and bot IDs
#     - When bot_ids are specified, empty arrays are included for bots with no stories
#     - When no bot_ids are specified, returns stories from all bots
    
#     Example URLs:
#     - All stories (paginated): /top-stories
#     - Specific bots: /top-stories?bot_id=1,2,3
#     - With timeframe: /top-stories?timeframe=1D
#     - Custom pagination: /top-stories?page=2&per_page=20
#     - Combined filters: /top-stories?bot_id=1,2&timeframe=1W&page=1&per_page=10
#     ''',
#     params=[
#         {
#             'name': 'page',
#             'in': 'query',
#             'description': 'Page number for pagination (default: 1)',
#             'type': 'integer',
#             'default': 1,
#             'minimum': 1,
#             'required': False
#         },
#         {
#             'name': 'per_page',
#             'in': 'query',
#             'description': 'Number of items per page (default: 10)',
#             'type': 'integer',
#             'default': 10,
#             'minimum': 1,
#             'required': False
#         },
#         {
#             'name': 'timeframe',
#             'in': 'query',
#             'description': 'Filter stories by timeframe',
#             'type': 'string',
#             'enum': ['1D', '1W', '1M'],
#             'required': False
#         },
#         {
#             'name': 'bot_id',
#             'in': 'query',
#             'description': '''Comma-separated list of bot IDs to filter by.
#                             If not provided, returns stories from all bots.
#                             Example: bot_id=1,2,3''',
#             'type': 'string',
#             'required': False
#         }
#     ],
#     responses={
#         '200': {
#             'description': 'Successfully retrieved top stories',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {
#                         'type': 'boolean',
#                         'example': True
#                     },
#                     'data': {
#                         'type': 'object',
#                         'description': 'Stories grouped by bot_id',
#                         'additionalProperties': {
#                             'type': 'array',
#                             'items': {
#                                 'type': 'object',
#                                 'properties': {
#                                     'id': {'type': 'integer', 'description': 'Article ID'},
#                                     'title': {'type': 'string', 'description': 'Article title'},
#                                     'content': {'type': 'string', 'description': 'Article content'},
#                                     'image': {'type': 'string', 'description': 'Image URL'},
#                                     'url': {'type': 'string', 'description': 'Article URL'},
#                                     'date': {'type': 'string', 'format': 'date-time', 'description': 'Article date'},
#                                     'bot_id': {'type': 'integer', 'description': 'Bot identifier'},
#                                     'is_top_story': {'type': 'boolean', 'description': 'Indicates if this is a top story'},
#                                     'timeframes': {
#                                         'type': 'array',
#                                         'description': 'Timeframes this article appears in',
#                                         'items': {
#                                             'type': 'object',
#                                             'properties': {
#                                                 'article_id': {'type': 'integer'},
#                                                 'timeframe': {'type': 'string', 'enum': ['1D', '1W', '1M']},
#                                                 'created_at': {'type': 'string', 'format': 'date-time'}
#                                             }
#                                         }
#                                     },
#                                     'created_at': {'type': 'string', 'format': 'date-time'},
#                                     'updated_at': {'type': 'string', 'format': 'date-time'}
#                                 }
#                             }
#                         }
#                     },
#                     'count': {'type': 'integer', 'description': 'Number of articles returned'},
#                     'total': {'type': 'integer', 'description': 'Total number of articles matching the query'},
#                     'page': {'type': 'integer', 'description': 'Current page number'},
#                     'pages': {'type': 'integer', 'description': 'Total number of pages'},
#                     'per_page': {'type': 'integer', 'description': 'Items per page'},
#                     'timeframe': {'type': 'string', 'description': 'Applied timeframe filter'},
#                     'queried_bots': {
#                         'type': 'array',
#                         'description': 'List of bot IDs that were queried',
#                         'items': {'type': 'integer'}
#                     }
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
#                             'Invalid bot_id format. Must be comma-separated integers (e.g., 1,2,3)',
#                             'Invalid timeframe: 2D. Must be one of: 1D, 1W, 1M',
#                             'Page number must be greater than 0',
#                             'Items per page must be greater than 0'
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


