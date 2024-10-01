#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# # Set environment variables
export FLASK_ENV=${FLASK_ENV:-development} # if FLASK_ENV not set in .env file, then this variable will be used.


# Start the application
if [ "$FLASK_ENV" = "development" ]; then
    echo "Starting Flask development server..."
    python run.py --host=0.0.0.0 --port=9000
else
    echo "Starting Gunicorn production server..."
    PORT=${PORT:-9000}
    # exec gunicorn --workers 3 --threads 2 --timeout 120 server:app
    exec gunicorn --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120 server:app
fi
