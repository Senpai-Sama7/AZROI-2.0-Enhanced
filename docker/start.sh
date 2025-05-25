#!/bin/bash
# Production startup script for AZROI Autonomous AI Architect

set -e

echo "Starting AZROI Autonomous AI Architect..."

# Wait for database to be ready
echo "Waiting for database connection..."
python -c "
import time
import psycopg2
from backend.config.production_config import ConfigurationManager

config = ConfigurationManager()
db_config = config.get_config().database

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(
            host=db_config.host,
            port=db_config.port,
            user=db_config.username,
            password=db_config.password,
            database=db_config.database,
            connect_timeout=5
        )
        conn.close()
        print('Database connection successful!')
        break
    except psycopg2.OperationalError:
        retry_count += 1
        print(f'Database connection attempt {retry_count}/{max_retries} failed. Retrying in 2 seconds...')
        time.sleep(2)
else:
    print('Failed to connect to database after maximum retries')
    exit(1)
"

# Run database migrations
echo "Running database migrations..."
cd backend && python -m alembic upgrade head

# Start the application
echo "Starting application server..."
exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-log \
    --log-level info
