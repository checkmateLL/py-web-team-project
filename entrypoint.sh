#!/bin/sh

export $(grep -v '^#' .env | xargs)

DB_HOST=$(echo $SQLALCHEMY_DATABASE_URL | awk -F'[@]' '{print $2}' | cut -d'/' -f1)
echo "Waiting for database to be ready..."
while ! nc -z $DB_HOST 5432; do
  sleep 1

done

echo "Database is ready!"
poetry run alembic upgrade head
exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000