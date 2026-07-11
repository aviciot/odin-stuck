-- 009_temporal_databases.sql
-- Creates Temporal's persistence databases inside them-postgres.
-- Runs automatically on first container boot (empty data dir).
-- For existing volumes run manually:
--   docker exec them-postgres psql -U them -c "CREATE DATABASE temporal;"
--   docker exec them-postgres psql -U them -c "CREATE DATABASE temporal_visibility;"

CREATE DATABASE temporal;
CREATE DATABASE temporal_visibility;
