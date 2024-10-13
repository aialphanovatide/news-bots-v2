#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# Set environment variables
export FLASK_ENV=${FLASK_ENV:-development}

# Function to check, create, and apply Alembic migrations
check_create_and_apply_migrations() {
    echo "Checking for pending database migrations..."
    
    # Check if migrations directory exists
    if [ ! -d "migrations" ]; then
        echo "Migrations directory not found. Initializing Flask-Migrate..."
        flask db init
        if [ $? -ne 0 ]; then
            echo "Error initializing Flask-Migrate. Exiting."
            exit 1
        fi
    fi

    # Get the current revision and the head revision
    current_rev=$(flask db current 2>/dev/null)
    head_rev=$(flask db heads 2>/dev/null)

    if [ -z "$current_rev" ] && [ -z "$head_rev" ]; then
        echo "No migrations found. Creating initial migration..."
        flask db migrate -m "Initial migration"
        if [ $? -eq 0 ]; then
            echo "Initial migration created successfully."
            flask db upgrade
        else
            echo "Error creating initial migration. Exiting."
            exit 1
        fi
    elif [ "$current_rev" != "$head_rev" ]; then
        echo "Pending migrations found. Applying migrations..."
        flask db upgrade
    else
        echo "Database schema is up to date."
    fi

    echo "Database migrations check complete."
}

# Function to start the Flask application
start_flask_app() {
    echo "Starting Flask application in $FLASK_ENV mode..."
    if [ "$FLASK_ENV" = "development" ]; then
        python run.py --host=0.0.0.0 --port=5000
    else
        PORT=${PORT:-5000}
        exec gunicorn --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120 run:app
    fi
}

# Main execution
echo "Initializing application..."

# Check and apply migrations
check_create_and_apply_migrations

# Start the Flask application
start_flask_app