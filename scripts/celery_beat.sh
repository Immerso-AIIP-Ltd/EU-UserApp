#!/usr/bin/env bash
set -e

echo "Starting Celery Beat Scheduler..."

# Wait for Redis to be available
echo "Waiting for Redis..."
echo "Checking Redis connection at ${APP_REDIS_HOST:-app-redis}:${APP_REDIS_PORT:-6379}..."
until python -c "import redis, os; r = redis.Redis(host=os.getenv('APP_REDIS_HOST', 'app-redis'), port=int(os.getenv('APP_REDIS_PORT', 6379)), password=os.getenv('APP_REDIS_PASS'), username=os.getenv('APP_REDIS_USER')); r.ping()"; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done
echo "Redis is up - proceeding"

# Function to gracefully stop Celery beat
cleanup() {
    echo "Shutting down Celery Beat..."
    # Send TERM signal to Celery beat
    pkill -TERM celery
    # Wait for graceful shutdown
    wait
}

# Trap the TERM signal to call the cleanup function
trap 'cleanup' SIGTERM SIGINT

# Remove existing schedule database to prevent conflicts
rm -f /tmp/celerybeat-schedule.db

# Start Celery beat scheduler
echo "Celery Beat is starting..."
exec celery -A app.cronjobs.celery_app.celery beat \
    --loglevel=info \
    --schedule=/tmp/celerybeat-schedule.db