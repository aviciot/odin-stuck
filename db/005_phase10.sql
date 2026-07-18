-- Phase 10: SSE edge + entry_point_type constraint update
-- Idempotent: safe to re-run
-- Apply with:
--   docker cp db/005_phase10.sql them-postgres:/tmp/them_005_phase10.sql
--   docker exec them-postgres psql -U them -d them -f /tmp/them_005_phase10.sql
BEGIN;

-- Originally updated entry_point_type constraint on them.applications.
-- That column was moved to them.entry_points by 010_app_entrypoints.sql.
-- This migration is now a safe no-op on a clean schema (the constraint no
-- longer exists on them.applications so the DROP IF EXISTS is harmless).
ALTER TABLE them.applications
    DROP CONSTRAINT IF EXISTS applications_entry_point_type_check;

COMMIT;
