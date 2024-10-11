#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# # Set environment variables
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

    # Check for existing migrations
    if [ -z "$(ls -A migrations/versions)" ]; then
        echo "No migrations found. Creating initial migration..."
        flask db migrate -m "Initial migration"
        if [ $? -ne 0 ]; then
            echo "Error creating initial migration. Exiting."
            exit 1
        fi
    fi

    # Apply any pending migrations
    echo "Applying migrations..."
    flask db upgrade
    if [ $? -ne 0 ]; then
        echo "Error applying migrations. Exiting."
        exit 1
    fi

    echo "Database migrations check complete."
}

# Check, create, and apply migrations
check_create_and_apply_migrations


# Start the application
if [ "$FLASK_ENV" = "development" ]; then
    echo "Starting Flask development server..."
    python run.py --host=0.0.0.0 --port=9000
else
    echo "Starting Gunicorn production server..."
    PORT=${PORT:-9000}
    # exec gunicorn --workers 3 --threads 2 --timeout 120 server:app
    exec gunicorn --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120 run:app
fi
