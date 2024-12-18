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
#     endpoint_route='/bot/{bot_id}/metrics',
#     method='get',
#     tag='Bots',
#     description='Get bot metrics with pagination and filtering',
#     detail_description='''
#     Retrieves metrics for a specific bot with pagination and date filtering options.
    
#     The endpoint returns:
#     - List of individual metric records
#     - Aggregated statistics across the returned metrics
#     - Pagination metadata
    
#     Metrics include:
#     - Runtime statistics
#     - Resource usage (CPU, memory)
#     - Article processing counts
#     - Error and filtering statistics
#     ''',
#     params=[
#         {
#             'name': 'bot_id',
#             'in': 'path',
#             'description': 'ID of the bot',
#             'required': True,
#             'type': 'integer'
#         },
#         {
#             'name': 'page',
#             'in': 'query',
#             'description': 'Page number (starts at 1)',
#             'required': False,
#             'type': 'integer',
#             'default': 1,
#             'minimum': 1
#         },
#         {
#             'name': 'per_page',
#             'in': 'query',
#             'description': 'Number of items per page',
#             'required': False,
#             'type': 'integer',
#             'default': 10,
#             'minimum': 1
#         },
#         {
#             'name': 'start_date',
#             'in': 'query',
#             'description': 'Filter metrics after this date (ISO format: YYYY-MM-DDTHH:MM:SS)',
#             'required': False,
#             'type': 'string',
#             'format': 'date-time'
#         },
#         {
#             'name': 'end_date',
#             'in': 'query',
#             'description': 'Filter metrics before this date (ISO format: YYYY-MM-DDTHH:MM:SS)',
#             'required': False,
#             'type': 'string',
#             'format': 'date-time'
#         }
#     ],
#     responses={
#         '200': {
#             'description': 'Metrics retrieved successfully',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'data': {
#                         'type': 'object',
#                         'properties': {
#                             'metrics': {
#                                 'type': 'array',
#                                 'items': {
#                                     'type': 'object',
#                                     'properties': {
#                                         'id': {'type': 'integer'},
#                                         'bot_id': {'type': 'integer'},
#                                         'start_time': {'type': 'string', 'format': 'date-time'},
#                                         'end_time': {'type': 'string', 'format': 'date-time'},
#                                         'total_runtime': {'type': 'number'},
#                                         'total_articles_found': {'type': 'integer'},
#                                         'articles_processed': {'type': 'integer'},
#                                         'articles_saved': {'type': 'integer'},
#                                         'cpu_percent': {'type': 'number'},
#                                         'memory_percent': {'type': 'number'},
#                                         'total_errors': {'type': 'integer'},
#                                         'error_reasons': {'type': 'object'},
#                                         'total_filtered': {'type': 'integer'},
#                                         'filter_reasons': {'type': 'object'}
#                                     }
#                                 }
#                             },
#                             'aggregated_stats': {
#                                 'type': 'object',
#                                 'properties': {
#                                     'total_runtime': {'type': 'number'},
#                                     'avg_cpu_percent': {'type': 'number'},
#                                     'avg_memory_percent': {'type': 'number'},
#                                     'total_articles_found': {'type': 'integer'},
#                                     'total_articles_processed': {'type': 'integer'},
#                                     'total_articles_saved': {'type': 'integer'},
#                                     'total_errors': {'type': 'integer'},
#                                     'total_filtered': {'type': 'integer'}
#                                 }
#                             },
#                             'pagination': {
#                                 'type': 'object',
#                                 'properties': {
#                                     'total_items': {'type': 'integer'},
#                                     'total_pages': {'type': 'integer'},
#                                     'current_page': {'type': 'integer'},
#                                     'per_page': {'type': 'integer'},
#                                     'has_next': {'type': 'boolean'},
#                                     'has_prev': {'type': 'boolean'}
#                                 }
#                             }
#                         }
#                     }
#                 }
#             }
#         },
#         '400': {
#             'description': 'Invalid parameters provided',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {
#                         'type': 'string',
#                         'description': 'Error message describing the invalid parameters'
#                     }
#                 }
#             }
#         },
#         '404': {
#             'description': 'Bot not found',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {
#                         'type': 'string',
#                         'description': 'Error message indicating bot was not found'
#                     }
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
#                         'description': 'Error message describing what went wrong'
#                     }
#                 }
#             }
#         }
#     }
# )

# ____Delete an endpoint____
# success, message = swagger.delete_endpoint(endpoint_route='/delete_bot/{bot_id}')
# print(message)


