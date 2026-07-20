-- audit_dead_objects.sql
-- Run against the live DB to surface potentially unused tables, columns,
-- indexes, and constraints.
--
-- Usage:
--   docker exec -it them-postgres psql -U them -d them -f /tmp/audit_dead_objects.sql
--
-- This script ONLY reads — no writes, no drops.
-- Review output manually before deciding what to remove.

\echo ''
\echo '=== 1. All tables in them schema with row counts ==='
SELECT
  t.table_name,
  pg_size_pretty(pg_total_relation_size(format('them.%I', t.table_name))) AS total_size,
  (SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
   WHERE n.nspname='them' AND c.relname=t.table_name) AS approx_rows
FROM information_schema.tables t
WHERE t.table_schema = 'them'
ORDER BY pg_total_relation_size(format('them.%I', t.table_name)) DESC;

\echo ''
\echo '=== 2. Duplicate indexes (redundant — exact same columns as another index) ==='
SELECT
  i1.indexname AS keep_index,
  i2.indexname AS redundant_index,
  i1.tablename,
  i1.indexdef
FROM pg_indexes i1
JOIN pg_indexes i2
  ON i1.schemaname = i2.schemaname
  AND i1.tablename = i2.tablename
  AND i1.indexname <> i2.indexname
  AND i1.indexdef = i2.indexdef
  AND i1.indexname < i2.indexname
WHERE i1.schemaname = 'them'
ORDER BY i1.tablename;

\echo ''
\echo '=== 3. Never-used indexes (zero scans since last stats reset) ==='
\echo '    NOTE: stats reset on container restart — low scan count != unused ==='
SELECT
  schemaname,
  relname AS table_name,
  indexrelname AS index_name,
  idx_scan AS scans_since_stats_reset,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'them'
  AND idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'   -- never drop PKs
ORDER BY pg_relation_size(indexrelid) DESC;

\echo ''
\echo '=== 4. Nullable columns that have never had a non-NULL value ==='
\echo '    (useful for spotting dead feature columns) ==='
DO $$
DECLARE
  r RECORD;
  cnt bigint;
  sql text;
BEGIN
  RAISE NOTICE 'Table | Column | Type | All-NULL?';
  FOR r IN
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'them'
      AND is_nullable = 'YES'
    ORDER BY table_name, column_name
  LOOP
    sql := format('SELECT COUNT(*) FROM them.%I WHERE %I IS NOT NULL', r.table_name, r.column_name);
    EXECUTE sql INTO cnt;
    IF cnt = 0 THEN
      RAISE NOTICE '  %.% (%) — ALL NULL (%)', r.table_name, r.column_name, r.data_type, cnt;
    END IF;
  END LOOP;
END;
$$;

\echo ''
\echo '=== 5. Tables with zero rows ==='
SELECT
  t.table_name,
  (SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
   WHERE n.nspname='them' AND c.relname=t.table_name) AS approx_rows
FROM information_schema.tables t
WHERE t.table_schema = 'them'
  AND (SELECT reltuples::bigint FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
       WHERE n.nspname='them' AND c.relname=t.table_name) = 0
ORDER BY t.table_name;

\echo ''
\echo '=== 6. Foreign keys with no matching rows in referenced table ==='
\echo '    (orphaned FK references — data integrity check) ==='
SELECT
  tc.table_name AS child_table,
  kcu.column_name AS child_column,
  ccu.table_name AS parent_table,
  ccu.column_name AS parent_column,
  tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'them'
ORDER BY tc.table_name;

\echo ''
\echo '=== 7. Known divergences: live DB vs migration scripts ==='
\echo ''
\echo '  ISSUE 1: agents_transport_check only allows a2a_async — omni_ws blocked'
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conname = 'agents_transport_check';

\echo ''
\echo '  ISSUE 2: idx_tasks_user_id exists in live DB but NOT in any migration file'
\echo '           (was added directly on the DB — add to 001_schema.sql to make it canonical)'
SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='them' AND indexname='idx_tasks_user_id';

\echo ''
\echo '  ISSUE 3: app_orchestrators.edges type in live DB vs SQLAlchemy model'
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema='them' AND table_name='app_orchestrators' AND column_name='edges';
\echo '  ^ Live DB is ARRAY(_text). models.py AppOrchestrator.edges is mapped as JSONB.'
\echo '    ORM writes passing a dict/list will fail at runtime.'

\echo ''
\echo '=== Audit complete ==='
