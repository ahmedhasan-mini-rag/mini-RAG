#!/bin/bash
set -e

echo "Running database migration..."
cd src/models/schemas/db/
alembic upgrade head

cd /app
exec "$@"
