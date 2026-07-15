-- Phase 14: App-scoped orchestrator instances (app_orchestrators)
-- Introduces them.app_orchestrators — one orchestrator instance per application, owned
-- by that application, holding its own copy of every config column from them.orchestrators.
-- Also:
--   • adds delegatable to them.orchestrators (backfilled from a2a_exposed)
--   • adds app_orchestrator_id FK to them.entry_points
--   • widens entry_point_type CHECK to include 'a2a'
-- Idempotent: safe to re-run.
-- Apply:
--   docker cp db/014_app_orchestrators.sql them-postgres:/tmp/them_014_app_orchestrators.sql
--   docker exec them-postgres psql -U them -d them -f /tmp/them_014_app_orchestrators.sql

BEGIN;

-- ── 1. Create them.app_orchestrators ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS them.app_orchestrators (
    id                              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id                  UUID        NOT NULL REFERENCES them.applications(id) ON DELETE CASCADE,
    orchestrator_id                 UUID        REFERENCES them.orchestrators(id) ON DELETE SET NULL,
    name                            TEXT        NOT NULL,
    node_id                         TEXT,
    kind                            TEXT        NOT NULL DEFAULT 'standard',
    delegatable                     BOOLEAN     NOT NULL DEFAULT FALSE,
    -- ── Config columns (cloned from them.orchestrators) ──────────────────────
    display_name                    TEXT,
    system_prompt                   TEXT,
    allowed_agent_ids               UUID[]      NOT NULL DEFAULT '{}',
    llm_provider                    TEXT,
    llm_model                       TEXT,
    llm_api_key_encrypted           TEXT,
    llm_base_url                    TEXT,
    max_iterations                  INTEGER     NOT NULL DEFAULT 10,
    max_parallel_tools              INTEGER     NOT NULL DEFAULT 3,
    rate_limit_rpm                  INTEGER,
    daily_budget_usd                NUMERIC(10,4),
    voice_enabled                   BOOLEAN     NOT NULL DEFAULT FALSE,
    transcription_provider          VARCHAR(32),
    transcription_model             VARCHAR(64),
    transcription_api_key_encrypted TEXT,
    tts_enabled                     BOOLEAN     NOT NULL DEFAULT FALSE,
    tts_provider                    TEXT,
    tts_voice                       TEXT,
    tts_api_key_encrypted           TEXT,
    memory_enabled                  BOOLEAN     NOT NULL DEFAULT FALSE,
    summarize_every_n_calls         INTEGER     NOT NULL DEFAULT 3,
    memory_raw_fallback_n           INTEGER     NOT NULL DEFAULT 5,
    summarizer_provider             TEXT,
    summarizer_model                TEXT,
    summarizer_api_key_encrypted    TEXT,
    edges                           TEXT[]      NOT NULL DEFAULT '{websocket}',
    history_window                  INTEGER     NOT NULL DEFAULT 20,
    budget_tokens                   INTEGER,
    enabled                         BOOLEAN     NOT NULL DEFAULT TRUE,
    -- ── Timestamps ───────────────────────────────────────────────────────────
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- ── Constraints ──────────────────────────────────────────────────────────
    CONSTRAINT uq_app_orchestrators_name        UNIQUE (name),
    CONSTRAINT ck_app_orchestrators_name_slug   CHECK  (name ~ '^[a-z0-9_-]{1,64}$'),
    CONSTRAINT ck_app_orchestrators_kind        CHECK  (kind IN ('standard', 'router', 'voice'))
);

CREATE INDEX IF NOT EXISTS idx_app_orchestrators_application_id
    ON them.app_orchestrators(application_id);
CREATE INDEX IF NOT EXISTS idx_app_orchestrators_name
    ON them.app_orchestrators(name);

-- ── 2. Add delegatable to them.orchestrators ─────────────────────────────────

-- Phase 1: add column
ALTER TABLE them.orchestrators
    ADD COLUMN IF NOT EXISTS delegatable BOOLEAN NOT NULL DEFAULT FALSE;

-- Backfill from a2a_exposed where they diverge
UPDATE them.orchestrators
SET delegatable = COALESCE(a2a_exposed, FALSE)
WHERE delegatable IS DISTINCT FROM COALESCE(a2a_exposed, FALSE);

-- ── 3. Add app_orchestrator_id FK to them.entry_points ───────────────────────

-- Phase 1: add nullable FK column
ALTER TABLE them.entry_points
    ADD COLUMN IF NOT EXISTS app_orchestrator_id UUID
        REFERENCES them.app_orchestrators(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_entry_points_app_orchestrator_id
    ON them.entry_points(app_orchestrator_id);

-- ── 4. Widen entry_point_type CHECK to include 'a2a' ─────────────────────────

-- DROP then re-ADD (Postgres does not support ALTER CHECK in place)
ALTER TABLE them.entry_points
    DROP CONSTRAINT IF EXISTS entry_points_entry_point_type_check;

ALTER TABLE them.entry_points
    ADD CONSTRAINT entry_points_entry_point_type_check
        CHECK (entry_point_type IN ('websocket', 'sse', 'webrtc', 'a2a'));

-- ── 5. Backfill app_orchestrators — one row per application ──────────────────

-- Clone config from the bound orchestrator, reusing its name as the runtime key.
-- Guarded: skips apps that already have an app_orchestrators row.
INSERT INTO them.app_orchestrators (
    id,
    application_id,
    orchestrator_id,
    name,
    node_id,
    kind,
    delegatable,
    display_name,
    system_prompt,
    allowed_agent_ids,
    llm_provider,
    llm_model,
    llm_api_key_encrypted,
    llm_base_url,
    max_iterations,
    max_parallel_tools,
    rate_limit_rpm,
    daily_budget_usd,
    voice_enabled,
    transcription_provider,
    transcription_model,
    transcription_api_key_encrypted,
    tts_enabled,
    tts_provider,
    tts_voice,
    tts_api_key_encrypted,
    memory_enabled,
    summarize_every_n_calls,
    memory_raw_fallback_n,
    summarizer_provider,
    summarizer_model,
    summarizer_api_key_encrypted,
    edges,
    history_window,
    budget_tokens,
    enabled,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    a.id,
    o.id,
    -- Slugify name; append row-number suffix if the same orch is shared by multiple apps
    -- so each instance gets a globally unique name (the runtime key).
    CASE
        WHEN ROW_NUMBER() OVER (PARTITION BY o.id ORDER BY a.id) = 1
        THEN LOWER(REGEXP_REPLACE(REGEXP_REPLACE(o.name, '[^a-zA-Z0-9_-]', '-', 'g'), '^-+|-+$', '', 'g'))
        ELSE LOWER(REGEXP_REPLACE(REGEXP_REPLACE(o.name, '[^a-zA-Z0-9_-]', '-', 'g'), '^-+|-+$', '', 'g'))
             || '-' || ROW_NUMBER() OVER (PARTITION BY o.id ORDER BY a.id)::text
    END,
    'orch-node-1',
    'standard',
    COALESCE(o.a2a_exposed, FALSE),
    o.display_name,
    o.system_prompt,
    o.allowed_agent_ids,
    o.llm_provider,
    o.llm_model,
    o.llm_api_key_encrypted,
    o.llm_base_url,
    o.max_iterations,
    o.max_parallel_tools,
    o.rate_limit_rpm,
    o.daily_budget_usd,
    o.voice_enabled,
    o.transcription_provider,
    o.transcription_model,
    o.transcription_api_key_encrypted,
    o.tts_enabled,
    o.tts_provider,
    o.tts_voice,
    o.tts_api_key_encrypted,
    o.memory_enabled,
    o.summarize_every_n_calls,
    o.memory_raw_fallback_n,
    o.summarizer_provider,
    o.summarizer_model,
    o.summarizer_api_key_encrypted,
    o.edges,
    o.history_window,
    o.budget_tokens,
    o.enabled,
    now(),
    now()
FROM them.applications a
JOIN them.orchestrators o ON o.id = a.orchestrator_id
WHERE NOT EXISTS (
    SELECT 1 FROM them.app_orchestrators ao WHERE ao.application_id = a.id
);

-- ── 6. Backfill entry_points.app_orchestrator_id ─────────────────────────────

-- Point each entry point at the app_orchestrators row created for its app.
-- Guarded: only updates EPs that are still NULL.
UPDATE them.entry_points ep
SET app_orchestrator_id = ao.id
FROM them.app_orchestrators ao
WHERE ao.application_id = ep.application_id
  AND ep.app_orchestrator_id IS NULL;

COMMIT;
