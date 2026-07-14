-- Phase 13: Agentic Middleware
BEGIN;

CREATE TABLE IF NOT EXISTS them.middleware_defs (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug          TEXT        NOT NULL UNIQUE,
    kind          TEXT        NOT NULL,
    display_name  TEXT        NOT NULL,
    description   TEXT        NOT NULL DEFAULT '',
    config        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    is_builtin    BOOLEAN     NOT NULL DEFAULT false,
    enabled       BOOLEAN     NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_mw_defs_kind CHECK (kind IN ('guard', 'cache'))
);

CREATE INDEX IF NOT EXISTS idx_mw_defs_kind ON them.middleware_defs(kind);

CREATE TABLE IF NOT EXISTS them.middleware_wirings (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID        NOT NULL
                        REFERENCES them.applications(id) ON DELETE CASCADE,
    agent_id        UUID        NOT NULL
                        REFERENCES them.agents(id) ON DELETE CASCADE,
    def_id          UUID        NOT NULL
                        REFERENCES them.middleware_defs(id) ON DELETE RESTRICT,
    position        INTEGER     NOT NULL DEFAULT 0,
    config_override JSONB       NOT NULL DEFAULT '{}'::jsonb,
    enabled         BOOLEAN     NOT NULL DEFAULT true,
    node_id         TEXT        NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_mw_wiring_app_agent_pos UNIQUE (application_id, agent_id, position)
);

CREATE INDEX IF NOT EXISTS idx_mw_wirings_app_agent
    ON them.middleware_wirings(application_id, agent_id);

INSERT INTO them.middleware_defs (slug, kind, display_name, description, config, is_builtin, enabled)
VALUES
(
    'guard_default',
    'guard',
    'Guard (PII + Prompt Injection)',
    'In-process PII detection and prompt-injection detection. Block or redact.',
    '{
        "mode": "redact",
        "checks": ["pii", "prompt_injection"],
        "pii_entities": ["EMAIL", "PHONE", "CREDIT_CARD", "SSN"],
        "on_block_message": "This request was blocked by a safety guard."
    }'::jsonb,
    true,
    true
),
(
    'cache_default',
    'cache',
    'Exact-Match Cache',
    'Redis-backed exact-match response cache. Scopes: global, app, session, user.',
    '{
        "ttl_seconds": 300,
        "scope": "global",
        "key_fields": ["message"],
        "max_result_chars": 100000
    }'::jsonb,
    true,
    true
)
ON CONFLICT (slug) DO NOTHING;

COMMIT;
