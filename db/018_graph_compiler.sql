-- Phase 18: Graph compiler invariants
-- Makes (application_id, node_id) a unique key on app_orchestrators so
-- the compiler can upsert by canvas node identity instead of guessing.
-- No new tables — typed tables remain the only persistence layer.
BEGIN;

-- Backfill any legacy rows that have no node_id yet
UPDATE them.app_orchestrators
   SET node_id = 'orch-' || id::text
 WHERE node_id IS NULL;

-- Now enforce NOT NULL + unique per app
ALTER TABLE them.app_orchestrators
    ALTER COLUMN node_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_orch_app_node
    ON them.app_orchestrators (application_id, node_id);

-- Same invariant for middleware wirings (already has node_id, make it meaningful)
CREATE UNIQUE INDEX IF NOT EXISTS uq_mw_wiring_app_node
    ON them.middleware_wirings (application_id, node_id)
    WHERE node_id IS NOT NULL AND node_id != '';

COMMIT;
