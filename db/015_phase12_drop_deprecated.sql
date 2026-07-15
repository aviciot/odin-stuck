-- Migration 015: Phase 12 — drop deprecated columns
-- Removes:
--   • them.orchestrators.a2a_exposed  (superseded by them.orchestrators.delegatable)
--   • them.applications.orchestrator_id  (superseded by them.app_orchestrators per-EP config)
--
-- BEFORE running: confirm all app rows have at least one app_orchestrators row (Phase 14
-- backfill in 014_app_orchestrators.sql ensures this).
--
-- This migration is idempotent — safe to re-run.

BEGIN;

-- ── 1. Drop them.orchestrators.a2a_exposed ────────────────────────────────────
-- Superseded by orchestrators.delegatable (added + backfilled in 014).
ALTER TABLE them.orchestrators
    DROP COLUMN IF EXISTS a2a_exposed;

-- ── 2. Drop them.applications.orchestrator_id ─────────────────────────────────
-- Superseded by the app_orchestrators table. Each entry point now owns its own
-- orchestrator instance. The FK constraint and index are dropped automatically.
ALTER TABLE them.applications
    DROP COLUMN IF EXISTS orchestrator_id;

COMMIT;
