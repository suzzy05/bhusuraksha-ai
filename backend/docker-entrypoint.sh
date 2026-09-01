#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ] && [ "${DATABASE_URL#sqlite}" = "$DATABASE_URL" ]; then
  echo "Running database migrations (alembic upgrade head)..."
  alembic upgrade head
else
  echo "SQLite database detected — schema is auto-created by the app at startup, skipping Alembic."
fi

echo "Starting BHUSURAKSHA AI backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
