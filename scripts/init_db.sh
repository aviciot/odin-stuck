#!/bin/bash
set -e

echo "=== Odin DB Init ==="

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-odin-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-odin-redis}"
ODIN_DB_USER="${ODIN_DB_USER:-odin}"
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

# Copy schema + seed files into container
docker cp "$PROJECT_DIR/db/001_schema.sql"       "$POSTGRES_CONTAINER:/tmp/odin_001_schema.sql"
docker cp "$PROJECT_DIR/auth_service/SCHEMA.sql" "$POSTGRES_CONTAINER:/tmp/odin_auth_schema.sql"
docker cp "$PROJECT_DIR/db/002_seed.sql"         "$POSTGRES_CONTAINER:/tmp/odin_002_seed.sql"

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

# Flush Redis orchestrator + agent cache so the bridge picks up fresh DB IDs.
# Without this, stale cached UUIDs cause FK violations on run inserts.
echo "Flushing Redis orchestrator/agent cache..."
if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
  docker exec "$REDIS_CONTAINER" redis-cli -n 0 \
    DEL odin:agents:registry \
    "odin:orchestrators:default" \
    > /dev/null
  echo "  Redis cache flushed."
else
  echo "  Redis container '$REDIS_CONTAINER' not running — skipping cache flush."
fi

echo ""
echo "=== Odin DB Init complete ==="
echo ""
echo "Agents seeded:"
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -c "SELECT slug, display_name, enabled FROM odin.agents ORDER BY slug;"
echo ""
echo "Orchestrators seeded:"
docker exec "$POSTGRES_CONTAINER" psql -U "$ODIN_DB_USER" -d "$ODIN_DB_NAME" \
  -c "SELECT name, display_name, llm_model, enabled FROM odin.orchestrators ORDER BY name;"
