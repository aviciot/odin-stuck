# Odin Test Index
# Last updated: 2026-07-02

All test scripts live in `scripts/tests/`. They are designed to be run both manually
during development and as part of the deployment checklist.

---

## Running Tests

```bash
# Run the full Phase 3 suite
bash scripts/tests/run_phase3_tests.sh

# Run individual test
bash scripts/tests/test_01_db.sh
python3 scripts/tests/test_07_adapter_factory.py

# Override defaults (containers/URLs)
BRIDGE_URL=http://localhost:8001 \
AUTH_SERVICE_URL=http://localhost:8701 \
POSTGRES_CONTAINER=omni-postgres \
REDIS_CONTAINER=omni-redis \
bash scripts/tests/run_phase3_tests.sh
```

---

## Test Scripts

| Script | Phase | Needs | What it tests |
|---|---|---|---|
| `test_01_db.sh` | 0 | Docker + omni-postgres | DB connectivity, odin schema, all tables exist |
| `test_02_redis.sh` | 0 | Docker + omni-redis | Redis DB 1 reachable, read/write, namespace isolation |
| `test_03_auth_service.sh` | 1 | odin-auth-service running | Auth service /health, /health/live, /health/ready |
| `test_04_bridge_health.sh` | 0/1 | odin-bridge running | Bridge /health, /health/live, /health/ready |
| `test_05_agents_api.sh` | 3 | odin-bridge running | Full agent CRUD: create, get, patch, delete, conflict, invalid transport |
| `test_06_orchestrators_api.sh` | 3 | odin-bridge running | Full orchestrator CRUD: create, get, patch, delete, conflict |
| `test_07_adapter_factory.py` | 3 | Python only (no containers) | AdapterEvent, factory routing, A2aAdapter stub, AgentAdapter ABC |
| `run_phase3_tests.sh` | 3 | All of the above | Runs tests 01-07 in order |

---

## Phase Test Suites (planned)

| Runner | Phase | Status |
|---|---|---|
| `run_phase3_tests.sh` | 3 — Adapters + Registry + Admin CRUD | ✓ Available |
| `run_phase4_tests.sh` | 4 — Token cache + Rate limiter | Pending |
| `run_phase5_tests.sh` | 5 — Orchestrator loop + WS endpoint | Pending |
| `run_phase6_tests.sh` | 6 — Dashboard WS + Runs API | Pending |
| `run_all_tests.sh` | Full suite | Pending |

---

## Deployment Checklist Order

When deploying Odin to a new environment:

1. `bash scripts/init_db.sh` — create DB + apply schema
2. `bash scripts/tests/test_01_db.sh` — verify DB
3. `bash scripts/tests/test_02_redis.sh` — verify Redis
4. Start auth service: `docker compose up -d odin-auth-service`
5. `bash scripts/tests/test_03_auth_service.sh` — verify auth
6. Start bridge: `docker compose up -d odin-bridge`
7. `bash scripts/tests/test_04_bridge_health.sh` — verify bridge
8. `bash scripts/tests/run_phase3_tests.sh` — full Phase 3 suite
9. Add seed data if needed: agents + orchestrators via API
10. Continue with Phase 4+ tests as each phase is built

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `BRIDGE_URL` | `http://localhost:8001` | odin-bridge base URL |
| `AUTH_SERVICE_URL` | `http://localhost:8701` | odin-auth-service base URL |
| `POSTGRES_CONTAINER` | `omni-postgres` | Docker container name for psql |
| `POSTGRES_DB` | `odin` | DB name |
| `POSTGRES_USER` | `odin` | DB user |
| `REDIS_CONTAINER` | `omni-redis` | Docker container name for redis-cli |
| `REDIS_DB` | `1` | Redis DB index |
