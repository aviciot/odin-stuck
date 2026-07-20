#!/usr/bin/env bash
# dump_db.sh — Take a full backup of the-M DB.
# Produces: db/them_full_dump_<timestamp>.sql (schema + all data)
# Also refreshes the canonical seed snapshots.
#
# Usage: ./db/dump_db.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PG_CONTAINER="them-postgres"
PG_USER="them"
PG_DB="them"
TS="$(date '+%Y%m%d_%H%M%S')"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

docker inspect -f '{{.State.Running}}' "$PG_CONTAINER" >/dev/null 2>&1 \
  || { echo "ERROR: $PG_CONTAINER is not running"; exit 1; }

log "--- Full dump (schema + data) ---"
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
  --no-owner --no-acl \
  -f "/tmp/them_full_dump_${TS}.sql"
docker cp "${PG_CONTAINER}:/tmp/them_full_dump_${TS}.sql" "${SCRIPT_DIR}/them_full_dump_${TS}.sql"
log "Full dump: db/them_full_dump_${TS}.sql ($(du -sh "${SCRIPT_DIR}/them_full_dump_${TS}.sql" | cut -f1))"

log "--- Refreshing canonical schema snapshots ---"
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
  --schema-only --schema=them --no-owner --no-acl -f /tmp/them_schema_init.sql
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
  --schema-only --schema=auth_service --no-owner --no-acl -f /tmp/them_auth_schema_init.sql
docker cp "${PG_CONTAINER}:/tmp/them_schema_init.sql" "${SCRIPT_DIR}/them_schema_init.sql"
docker cp "${PG_CONTAINER}:/tmp/them_auth_schema_init.sql" "${SCRIPT_DIR}/them_auth_schema_init.sql"
log "Schema snapshots refreshed"

log "--- Refreshing structural seed snapshots ---"
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
  --data-only --schema=them --no-owner --no-acl \
  -t them.llm_providers -t them.config -t them.agents -t them.orchestrators \
  -t them.applications -t them.entry_points -t them.app_orchestrators \
  -t them.middleware_defs -t them.middleware_wirings \
  -f /tmp/them_seed_data.sql
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" \
  --data-only --schema=auth_service --no-owner --no-acl \
  -t auth_service.roles -t auth_service.users -t auth_service.teams -t auth_service.team_members \
  -f /tmp/them_auth_seed_data.sql
docker cp "${PG_CONTAINER}:/tmp/them_seed_data.sql" "${SCRIPT_DIR}/them_seed_data.sql"
docker cp "${PG_CONTAINER}:/tmp/them_auth_seed_data.sql" "${SCRIPT_DIR}/them_auth_seed_data.sql"
log "Seed snapshots refreshed"

log "=== Done ==="
