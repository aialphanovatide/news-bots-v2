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

# success, message = swagger.add_or_update_endpoint(
#     endpoint_route='/bot',
#     method='post',
#     tag='Bots',
#     description='Create a new bot',
#     detail_description='''
#     This endpoint allows you to create a new bot with specified parameters.
    
#     Key points:
#     - The 'name', 'alias', and 'category_id' fields are required.
#     - The 'prompt' field is required and should contain the bot's initial conversation prompt.
#     - The 'run_frequency' is optional and specifies how often the bot should run (in minutes).
#     - The 'dalle_prompt' is optional and can be used to generate a custom icon for the bot.
#     - The 'background_color' is optional and can be used to set a custom background color for the bot's icon.
#     - The 'created_at' and 'updated_at' timestamps are automatically set.

#     After creation, the bot will be associated with the specified category and can be managed through other bot-related endpoints.
#     ''',
#     params=[
#         {
#             'name': 'body',
#             'in': 'body',
#             'description': 'Bot details',
#             'required': True,
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'name': {'type': 'string', 'description': 'Name of the bot (required)'},
#                     'alias': {'type': 'string', 'description': 'Unique identifier for the bot (required)'},
#                     'category_id': {'type': 'integer', 'description': 'ID of the category the bot belongs to (required)'},
#                     'prompt': {'type': 'string', 'description': 'Initial conversation prompt for the bot (required)'},
#                     'run_frequency': {'type': 'integer', 'description': 'How often the bot should run, in minutes (optional)'},
#                     'dalle_prompt': {'type': 'string', 'description': 'Prompt for generating a custom icon using DALL-E (optional)'},
#                     'background_color': {'type': 'string', 'description': 'Background color for the bot\'s icon (optional)'},
#                 },
#                 'required': ['name', 'alias', 'category_id', 'prompt']
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
#                     'data': {
#                         'type': 'array',
#                         'items': {
#                             'type': 'object',
#                             'properties': {
#                                 'id': {'type': 'integer', 'description': 'Unique identifier for the bot'},
#                                 'name': {'type': 'string', 'description': 'Name of the bot'},
#                                 'alias': {'type': 'string', 'description': 'Unique alias of the bot'},
#                                 'category_id': {'type': 'integer', 'description': 'ID of the category the bot belongs to'},
#                                 'prompt': {'type': 'string', 'description': 'Initial conversation prompt for the bot'},
#                                 'run_frequency': {'type': 'integer', 'description': 'How often the bot runs, in minutes'},
#                                 'dalle_prompt': {'type': 'string', 'description': 'Prompt used for generating the bot\'s icon'},
#                                 'icon': {'type': 'string', 'description': 'URL of the bot\'s icon'},
#                                 'background_color': {'type': 'string', 'description': 'Background color of the bot\'s icon'},
#                                 'created_at': {'type': 'string', 'format': 'date-time', 'description': 'Timestamp of when the bot was created'},
#                                 'updated_at': {'type': 'string', 'format': 'date-time', 'description': 'Timestamp of when the bot was last updated'}
#                             }
#                         }
#                     }
#                 }
#             }
#         },
#         '400': {
#             'description': 'Invalid input - This could occur if required fields are missing or if the alias is not unique',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {'type': 'string'}
#                 }
#             }
#         },
#         '500': {
#             'description': 'Internal server error - This could occur due to database issues or other server-side problems',
#             'schema': {
#                 'type': 'object',
#                 'properties': {
#                     'success': {'type': 'boolean'},
#                     'error': {'type': 'string'}
#                 }
#             }
#         }
#     }
# )

# print(message)


# ____Delete an endpoint____

# success, message = swagger.delete_endpoint(endpoint_route='/delete_bot/{bot_id}')
# print(message)


