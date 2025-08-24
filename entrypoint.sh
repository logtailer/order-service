#!/bin/sh
set -e

# Function to wait for postgres
wait_for_postgres() {
  until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
  done
  >&2 echo "Postgres is up - continuing"
}

# Apply database migrations
run_migrations() {
  echo "Applying database migrations..."
  cd /order-service
  FLASK_APP=run.py python -m flask db upgrade
  echo "Migrations complete"
}

# Start the application
start_app() {
  echo "Starting application..."
  exec python run.py
}

# Main execution flow
if [ "${1}" = "migrate" ]; then
  wait_for_postgres
  run_migrations
elif [ "${1}" = "app" ]; then
  wait_for_postgres
  run_migrations
  start_app
else
  exec "$@"
fi
