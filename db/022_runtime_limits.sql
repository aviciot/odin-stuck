-- Migration 022: runtime management — per-EP concurrent session cap
-- Enforced at connection time via Redis SCARD (atomic Lua check-and-add).
-- NULL = unlimited.

ALTER TABLE them.entry_points
  ADD COLUMN IF NOT EXISTS max_concurrent_sessions INTEGER;

COMMENT ON COLUMN them.entry_points.max_concurrent_sessions IS
  'Max simultaneous active sessions for this entry point. NULL = unlimited. Enforced by runtime_manager.runtime_gate via atomic Lua EVAL on them:ep:{slug}:sessions.';
