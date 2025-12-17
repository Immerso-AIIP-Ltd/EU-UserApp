#!/usr/bin/env bash
set -e

# Function to gracefully stop Celery processes
cleanup() {
    echo "Shutting down Celery..."
    # Terminate all child processes
    pkill -P $$
    wait
}

# Trap the TERM signal to call the cleanup function
trap 'cleanup' SIGTERM

# Start Celery worker in the background
celery -A app.cronjobs.celery_app.celery worker --loglevel=info &

# Start Celery Beat in the background
celery -A app.cronjobs.celery_app.celery beat --loglevel=info &

# Wait for any background process to exit
wait -n