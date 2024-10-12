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

# POST /category
success, message = swagger.add_or_update_endpoint(
    endpoint_route='/category',
    method='post',
    tag='Categories',
    description='Create a new category for organizing bots',
    detail_description='''
    This endpoint allows you to create a new category, which serves as a container for grouping related bots.
    
    Key points:
    - The 'name' and 'alias' fields are required. The 'name' is displayed to users, while the 'alias' is used internally.
    - An icon URL is automatically generated based on the provided alias. This icon will be used in the UI to represent the category.
    - The 'slack_channel' field, if provided, associates the category with a specific Slack channel for notifications.
    - The 'border_color' field allows you to set a custom color (in HEX format) for visual distinction in the UI.
    - New categories are created with 'is_active' set to false by default.
    - The 'created_at' and 'updated_at' timestamps are automatically set.

    After creation, you can add bots to this category using the bot creation or update endpoints.
    ''',
    params=[
        {
            'name': 'body',
            'in': 'body',
            'description': 'Category details',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'Display name of the category (required)'},
                    'alias': {'type': 'string', 'description': 'Unique identifier for the category, used for icon generation (required)'},
                    'slack_channel': {'type': 'string', 'description': 'Slack channel ID for category notifications (optional)'},
                    'border_color': {'type': 'string', 'description': 'HEX color code for category border in UI (optional, e.g., "#FF5733")'},
                },
                'required': ['name', 'alias']
            }
        }
    ],
    responses={
        '201': {
            'description': 'Category created successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {'$ref': '#/components/schemas/Category'}
                }
            }
        },
        '400': {
            'description': 'Invalid input - This could occur if required fields are missing or if the alias is not unique',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': 'Internal server error - This could occur due to database issues or other server-side problems',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
)

print(message)

# PUT /category/{category_id}
success, message = swagger.add_or_update_endpoint(
    endpoint_route='/category/{category_id}',
    method='put',
    tag='Categories',
    description='Update an existing category',
    detail_description='''
    This endpoint allows you to update the details of an existing category. It's particularly useful for modifying category properties or correcting information.

    Key behaviors:
    1. Partial updates are supported. You only need to include the fields you want to change in the request body.
    2. If the 'alias' is updated, the category's icon URL will be automatically regenerated.
    3. Updating certain fields (like 'slack_channel' or 'run_frequency') will trigger a rescheduling of all active bots in this category.
    4. The 'updated_at' timestamp is automatically set to the current time upon successful update.

    Important notes for frontend implementation:
    - When updating the 'alias', be aware that this might change the category's icon, which could affect UI elements.
    - If the update results in bot rescheduling, the response will include information about which bots were rescheduled or if any failed.
    - The 'border_color' field accepts HEX color codes, which can be used to update the category's visual representation in the UI.

    This endpoint is crucial for maintaining accurate and up-to-date category information, which directly impacts bot organization and functionality.
    ''',
    params=[
        {
            'name': 'category_id',
            'in': 'path',
            'description': 'Unique identifier of the category to update',
            'required': True,
            'type': 'integer'
        },
        {
            'name': 'body',
            'in': 'body',
            'description': 'Updated category details',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'New display name for the category'},
                    'alias': {'type': 'string', 'description': 'New alias for the category (will regenerate icon URL if changed)'},
                    'slack_channel': {'type': 'string', 'description': 'New Slack channel ID for category notifications'},
                    'border_color': {'type': 'string', 'description': 'New HEX color code for category border in UI (e.g., "#FF5733")'},
                }
            }
        }
    ],
    responses={
        '200': {
            'description': 'Category updated successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'category': {'$ref': '#/components/schemas/Category'},
                            'rescheduled_bots': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Names of bots that were rescheduled due to the update'
                            },
                            'failed_reschedules': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Names of bots that failed to reschedule'
                            }
                        }
                    }
                }
            }
        },
        '404': {
            'description': 'Category not found - The specified category_id does not exist',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': 'Internal server error - This could occur due to database issues or problems with the scheduler',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
)

print(message)

# POST /category/{category_id}/toggle-activation
success, message = swagger.add_or_update_endpoint(
    endpoint_route='/category/{category_id}/toggle-activation',
    method='post',
    tag='Categories',
    description='Toggle activation status for all bots in a category',
    detail_description='''
    This endpoint provides a powerful way to activate or deactivate all bots within a specific category simultaneously. It's particularly useful for bulk operations or when you need to quickly enable or disable a group of related bots.

    Key behaviors:
    1. If the category is currently active (contains active bots):
       - All active bots will be deactivated.
       - Their scheduled jobs will be removed from the scheduler.
       - Each bot's 'is_active' status will be set to false.
       - Each bot's status will be changed to 'IDLE'.
       - The 'next_run_time' for each bot will be cleared.

    2. If the category is currently inactive (contains no active bots):
       - Each bot in the category will be validated for activation.
       - If a bot passes validation, it will be scheduled and activated.
       - The bot's 'is_active' status will be set to true.
       - The bot's status will be set to 'IDLE' (it will change to 'RUNNING' when the scheduler executes it).

    Important notes for frontend implementation:
    - This operation may take some time, especially for categories with many bots.
    - The response includes detailed information about the operation's results, including counts of activated/deactivated bots and any failures.
    - You may want to implement a loading indicator while this operation is in progress.
    - After toggling, you should refresh any UI components that display bot statuses or category information.
    - Be prepared to handle partial success scenarios where some bots may fail to activate or deactivate.

    This endpoint is crucial for managing the overall activity of bot groups and can significantly impact system resource usage and bot operations.
    ''',
    params=[
        {
            'name': 'category_id',
            'in': 'path',
            'description': 'Unique identifier of the category whose bots should be toggled',
            'required': True,
            'type': 'integer'
        }
    ],
    responses={
        '200': {
            'description': 'Category bots toggled successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'total_bots': {'type': 'integer', 'description': 'Total number of bots in the category'},
                            'activated_count': {'type': 'integer', 'description': 'Number of bots that were activated'},
                            'deactivated_count': {'type': 'integer', 'description': 'Number of bots that were deactivated'},
                            'success_count': {'type': 'integer', 'description': 'Total number of bots successfully processed'},
                            'failure_count': {'type': 'integer', 'description': 'Number of bots that failed to toggle'},
                            'processed_bots': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'integer', 'description': 'Bot ID'},
                                        'name': {'type': 'string', 'description': 'Bot name'},
                                        'previous_state': {'type': 'string', 'description': 'Bot state before toggling'},
                                        'new_state': {'type': 'string', 'description': 'Bot state after toggling'},
                                        'status': {'type': 'string', 'description': 'Status of the toggle operation for this bot'},
                                        'error': {'type': 'string', 'description': 'Error message if the bot failed to toggle'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        '404': {
            'description': 'Category not found - The specified category_id does not exist',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': 'Internal server error - This could occur due to database issues, problems with the scheduler, or other server-side errors',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
)

print(message)

# ____Delete an endpoint____

# success, message = swagger.delete_endpoint(endpoint_route='/delete_bot/{bot_id}')
# print(message)


