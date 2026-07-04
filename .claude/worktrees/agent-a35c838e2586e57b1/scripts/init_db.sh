#!/bin/bash
set -e

echo "=== Odin DB Init ==="

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-odin-postgres}"
ODIN_DB_USER="${ODIN_DB_USER:-odin}"
ODIN_DB_PASSWORD="${ODIN_DB_PASSWORD:-odin_secret}"
ODIN_DB_NAME="${ODIN_DB_NAME:-odin}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Wait for Postgres to be ready
echo "Waiting for Postgres..."
for i in $(seq 1 20); do
  docker exec "$POSTGRES_CONTAINER" pg_isready -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" > /dev/null 2>&1 && break
  echo "  ... not ready yet ($i/20)"
  sleep 2
done

# The odin user and database are created by the Postgres container itself
# (via POSTGRES_USER / POSTGRES_DB env vars). Just apply schemas.

# Copy schema files
docker cp "$PROJECT_DIR/db/001_schema.sql"          "$POSTGRES_CONTAINER:/tmp/odin_001_schema.sql"
docker cp "$PROJECT_DIR/auth_service/SCHEMA.sql"    "$POSTGRES_CONTAINER:/tmp/odin_auth_schema.sql"
docker cp "$PROJECT_DIR/db/002_seed.sql"            "$POSTGRES_CONTAINER:/tmp/odin_002_seed.sql"

echo "Creating auth_service schema..."
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -c "CREATE SCHEMA IF NOT EXISTS auth_service;"

echo "Applying odin schema..."
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -f /tmp/odin_001_schema.sql

echo "Applying auth_service schema..."
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -f /tmp/odin_auth_schema.sql

echo "Applying seed data..."
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -f /tmp/odin_002_seed.sql

echo "=== Odin DB Init complete ==="
