-- Migration 023: application runtime — per-app runtime policy config (JSONB).
-- Enforced at connection time by runtime_manager.runtime_gate BEFORE entry-point gate.
-- Empty object {} = no limits. Supported keys:
--   max_concurrent_sessions INTEGER  — app-wide soft session cap (SCARD read)
--   rate_limit_rpm          INTEGER  — app-level requests-per-minute (INCR rl:them:app:{id}:{slot})
--   blocked_tokens          TEXT[]   — sha256 hashes of blocked access tokens
--   blocked_user_ids        INTEGER[]— user_ids barred from this app
--   session_timeout_minutes INTEGER  — advisory (future: enforced via session_manager TTL)

ALTER TABLE them.applications
  ADD COLUMN IF NOT EXISTS runtime_config JSONB NOT NULL DEFAULT '{}';

COMMENT ON COLUMN them.applications.runtime_config IS
  'App-level runtime policy: {max_concurrent_sessions, rate_limit_rpm, blocked_tokens[], blocked_user_ids[], session_timeout_minutes}. Enforced by runtime_manager.runtime_gate. {} = unlimited.';
