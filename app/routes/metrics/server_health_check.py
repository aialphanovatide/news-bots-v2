# Server health check endpoint

import psutil
from flask import Blueprint, jsonify
from flask import current_app, render_template
from app.routes.routes_utils import create_response

health_check_bp = Blueprint('health_check', __name__,
                            template_folder='templates')

@health_check_bp.route('/', methods=['GET'])
def welcome():
    """
    Welcome route to render a simple welcome message with system metrics.

    This endpoint does not take any parameters and returns a welcome HTML page
    containing various system metrics.

    Returns:
        flask.Response: A rendered HTML template with system metrics.

    Metrics included:
        - CPU usage
        - Memory usage
        - Number of active threads
        - System uptime
        - Count of registered routes

    Response:
        200: Welcome page rendered successfully with system metrics.
    """
    metrics = {
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'active_threads': len(psutil.Process().threads()),
        'uptime': int(psutil.boot_time()),
        'routes_count': len(current_app.url_map._rules)
    }
    return render_template('server_health_check.html', metrics=metrics)



