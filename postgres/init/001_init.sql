-- Postgres auto-init script — runs on first container boot (empty data dir only)
-- Creates the them schema and auth_service schema.
-- For subsequent schema changes, use scripts/init_db.sh instead.

-- Grant all on them DB to them user (already owner, but be explicit)
GRANT ALL PRIVILEGES ON DATABASE them TO them;
