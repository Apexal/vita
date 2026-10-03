#!/bin/sh
set -e

cleanup() {
    echo "Shutting down..."
    kill "$CRONIC_PID" "$WORKER_PID" "$DAPHNE_PID" 2>/dev/null || true
    wait "$CRONIC_PID" "$WORKER_PID" "$DAPHNE_PID" 2>/dev/null || true
    exit 0
}

trap cleanup TERM INT

echo "Starting supercronic..."
supercronic /code/crontab &
CRONIC_PID=$!

# Migrate here rather than via fly.toml's release_command: release machines
# don't mount volumes, so they'd migrate a throwaway SQLite file.
echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting db_worker..."
python manage.py db_worker &
WORKER_PID=$!

echo "Starting Daphne..."
python -m daphne vita.asgi:application -b 0.0.0.0 -p "${PORT:-8000}" &
DAPHNE_PID=$!

wait "$DAPHNE_PID"
