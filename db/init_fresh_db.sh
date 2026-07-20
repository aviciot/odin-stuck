#!/usr/bin/env bash
# init_fresh_db.sh — Full DB initialisation for the-M on a fresh server.
# Applies schema + seed from the canonical snapshots in db/.
# Run this ONCE after first `docker compose up -d`.
# Safe to re-run: all DDL uses IF NOT EXISTS / IF EXISTS guards.
#
# Usage:
#   ./db/init_fresh_db.sh                  # schema + structural seed
#   ./db/init_fresh_db.sh --schema-only    # schema only, no seed data
#   ./db/init_fresh_db.sh --seed-only      # seed only (schema already applied)
#
# Requires: docker, them-postgres container running, them-redis container running.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PG_CONTAINER="them-postgres"
PG_USER="them"
PG_DB="them"
REDIS_CONTAINER="them-redis"

SCHEMA_ONLY=false
SEED_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--schema-only" ]] && SCHEMA_ONLY=true
  [[ "$arg" == "--seed-only" ]] && SEED_ONLY=true
done

log() { echo "[$(date '+%H:%M:%S')] $*"; }
run_sql_file() {
  local label="$1" file="$2"
  local remote="/tmp/them_init_$(basename "$file")"
  docker cp "$file" "${PG_CONTAINER}:${remote}"
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -f "$remote" -v ON_ERROR_STOP=1
  log "  OK: $label"
}

log "=== the-M DB initialisation ==="

# Verify containers are up
docker inspect -f '{{.State.Running}}' "$PG_CONTAINER" >/dev/null 2>&1 \
  || { echo "ERROR: $PG_CONTAINER is not running"; exit 1; }

if [[ "$SEED_ONLY" == false ]]; then
  log "--- Applying schemas ---"

  # Create schemas
  docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
    -c "CREATE SCHEMA IF NOT EXISTS them;" \
    -c "CREATE SCHEMA IF NOT EXISTS auth_service;"

  # auth_service schema (auth microservice tables — owned by auth-service app)
  run_sql_file "auth_service schema" "$SCRIPT_DIR/them_auth_schema_init.sql"

  # them schema (all orchestrator tables)
  run_sql_file "them schema" "$SCRIPT_DIR/them_schema_init.sql"

  log "--- Schema complete ---"
fi

if [[ "$SCHEMA_ONLY" == false ]]; then
  log "--- Applying seed data ---"

  run_sql_file "auth_service seed (roles, users, teams)" "$SCRIPT_DIR/them_auth_seed_data.sql"
  run_sql_file "them structural seed (agents, orchestrators, apps, ...)" "$SCRIPT_DIR/them_seed_data.sql"

  log "--- Seed complete ---"
fi

# Bust Redis caches so bridge picks up fresh DB state immediately
if docker inspect -f '{{.State.Running}}' "$REDIS_CONTAINER" >/dev/null 2>&1; then
  log "Busting Redis caches..."
  docker exec "$REDIS_CONTAINER" redis-cli DEL \
    them:agents:registry \
    them:orchestrators:default \
    them:orchestrators:a2a_test \
    >/dev/null
  log "Redis caches cleared"
else
  log "WARNING: $REDIS_CONTAINER not running — skipping Redis cache bust"
fi

log "=== Done. the-M DB is ready. ==="
log "    Frontend: http://localhost:8088"
log "    Login:    admin / admin123"
