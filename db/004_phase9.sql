-- Phase 9: A2A production hardening + pluggable entry points
-- Idempotent: safe to re-run
-- Apply with:
--   docker cp db/004_phase9.sql them-postgres:/tmp/them_004_phase9.sql
--   docker exec them-postgres psql -U them -d them -f /tmp/them_004_phase9.sql
BEGIN;

-- tasks.user_id: ownership tracking for access isolation
ALTER TABLE them.tasks ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES auth_service.users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON them.tasks(user_id);

-- applications: user-composable agentic apps bound to an orchestrator + entry point
CREATE TABLE IF NOT EXISTS them.applications (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    slug             TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9_-]{1,64}$'),
    entry_point_type TEXT NOT NULL CHECK (entry_point_type IN ('websocket_chat','rest','voice','webrtc')),
    orchestrator_id  UUID NOT NULL REFERENCES them.orchestrators(id) ON DELETE CASCADE,
    access_policy    JSONB NOT NULL DEFAULT '{"mode":"token"}',
    presentation     JSONB NOT NULL DEFAULT '{}',
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
