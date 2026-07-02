# Odin — Multi-Agent Orchestration Platform

> Route any user goal through a pool of AI agents. Each agent is a tool. The LLM decides which ones to call, in what order, in parallel — then streams the answer back.

---

## What is Odin?

Odin is a production-grade **multi-agent orchestration platform** built on a clean agentic loop:

```
User message
    ↓
WebSocket /ws/orchestrate/{name}
    ↓
Load orchestrator config (system prompt, allowed agents, limits)
    ↓
Build LLM tool list  ←  each enabled agent = one NeutralTool named agent__<slug>
    ↓
Agentic loop (≤ max_iterations)
    LLM picks tools → parallel fan-out via adapters → stream results → feed back to LLM
    ↓
Stream final answer to client
```

Agents are transport-agnostic. Today: WebSocket to Omni agents (`omni_ws`). Tomorrow: A2A, HTTP, gRPC — just add an adapter.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              odin-network                │
                    │                                          │
  Browser / Client  │  ┌──────────────┐   ┌────────────────┐  │
  ───────────────►  │  │ odin-bridge  │   │ odin-auth-svc  │  │
  WS + REST API     │  │  (FastAPI)   │◄──│  (FastAPI)     │  │
                    │  │  port 8001   │   │  port 8701     │  │
                    │  └──────┬───────┘   └───────┬────────┘  │
                    │         │                   │            │
                    │  ┌──────▼───────────────────▼────────┐  │
                    │  │         odin-postgres (PG 16)      │  │
                    │  │  schema: odin  +  auth_service     │  │
                    │  └────────────────────────────────────┘  │
                    │  ┌────────────────────────────────────┐  │
                    │  │         odin-redis (Redis 7)        │  │
                    │  │  token cache · rate limits · pubsub │  │
                    │  └────────────────────────────────────┘  │
                    │                                          │
                    │  ┌────────────────────────────────────┐  │
                    │  │    odin-frontend (Next.js 16)       │  │
                    │  │         port 3200                   │  │
                    │  └────────────────────────────────────┘  │
                    └─────────────────────────────────────────┘
```

**Fully isolated.** Zero dependency on any external stack — own Postgres, own Redis, own network. All data is bind-mounted under `volumes/` and survives `docker compose down --build`.

---

## Stack

| Layer | Technology |
|---|---|
| Orchestrator API | Python 3.12 · FastAPI · asyncpg · SQLAlchemy async |
| Auth service | Python 3.12 · FastAPI · bcrypt · JWT (HS256) |
| Database | PostgreSQL 16 |
| Cache / PubSub | Redis 7 · AOF persistence |
| Frontend | Next.js 16 · TypeScript · Tailwind CSS 4 · Zustand |
| Container | Docker Compose · Traefik-ready labels |

---

## Features

### Core orchestration
- **Agentic loop** — LLM drives tool selection over multiple iterations
- **Parallel fan-out** — multiple tool calls in a single iteration via `asyncio.gather()`, bounded by `max_parallel_tools` and per-agent `max_concurrency`
- **WebSocket streaming** — tokens stream to the client in real time; tool start/done events visible as they happen
- **Run recording** — every run, step, token count and cost written to Postgres

### Agent registry
- CRUD API for agents with transport validation
- Auth tokens stored **Fernet-encrypted** at rest
- L1 (in-process) + L2 (Redis) cache with pub/sub invalidation — zero DB queries on the hot path

### Auth & access control
- **Two auth paths**: opaque Bearer tokens for WS orchestration; JWT for admin REST API
- Bearer tokens: sha256 hashed at rest, L1+L2 cached (TTL 300s), `last_used_at` tracked
- Rate limiting: Redis INCR fixed-window per user per hour
- bcrypt (cost 12) for user passwords — same approach as production Omni

### Dashboard
- WebSocket `/ws/dashboard` — multiplexed channels: `runs`, `agents`, `metrics`
- Redis pub/sub relay to connected clients in real time
- REST `/api/v1/runs` — paginated run history, stats, per-run step detail

### Frontend
- Login page with animated SVG logo, mesh-gradient background, glass-morphism card
- Dashboard: stat bento, infrastructure health, agent list, recent runs (30s auto-refresh)
- Agents page: searchable table with transport badges
- Runs page: full log with status, duration, token count, cost

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- An Anthropic API key (for the LLM in the orchestrator)

### 1. Clone and configure
```bash
git clone <repo>
cd odin
cp .env.example .env
# Edit .env — fill in ODIN_DB_PASSWORD, ODIN_SECRET_KEY, ODIN_JWT_SECRET, ANTHROPIC_API_KEY
```

### 2. Start the stack
```bash
docker compose up -d
```

### 3. Verify everything is healthy
```bash
bash scripts/tests/run_all_tests.sh
```

### 4. Create your first admin user
```bash
# Generate bcrypt hash inside the auth container
HASH=$(docker exec odin-auth-service python3 -c \
  "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())")

# Seed role + user
docker exec odin-postgres psql -U odin -d odin -c "
INSERT INTO auth_service.roles (name, description, mcp_access, tool_restrictions, dashboard_access, rate_limit, cost_limit_daily, token_expiry)
VALUES ('super_admin', 'Full system access', ARRAY['*'], '{}', 'admin', 10000, 1000.00, 7200)
ON CONFLICT (name) DO NOTHING;

INSERT INTO auth_service.users (username, name, email, password_hash, role_id, active)
SELECT 'admin', 'Admin', 'admin@odin.local', '$HASH', r.id, true
FROM auth_service.roles r WHERE r.name = 'super_admin';
"
```

### 5. Open the dashboard
```
http://localhost:3200
```

---

## Container Map

| Container | Role | Port |
|---|---|---|
| `odin-postgres` | PostgreSQL 16 | internal |
| `odin-redis` | Redis 7 (AOF) | internal |
| `odin-auth-service` | Auth / IAM microservice | 8701 (internal) |
| `odin-bridge` | Orchestrator API + WebSocket | 8001 (internal) |
| `odin-frontend` | Next.js dashboard | **3200** |

Traefik labels are pre-configured. Set `ODIN_HOSTNAME` and `ODIN_UI_HOSTNAME` in `.env` for automatic routing.

---

## API Reference

### Auth service (port 8701)
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Login → JWT + refresh token |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/validate` | Validate JWT |

### Bridge (port 8001)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` `/health/live` `/health/ready` | — | Health checks |
| WS | `/ws/orchestrate/{name}` | Bearer token | Run an orchestrator |
| WS | `/ws/dashboard` | JWT | Live event stream |
| GET/POST/PATCH/DELETE | `/api/v1/admin/agents` | JWT admin | Agent registry |
| GET/POST/PATCH/DELETE | `/api/v1/admin/orchestrators` | JWT admin | Orchestrator configs |
| GET/POST/PATCH/DELETE | `/api/v1/admin/tokens` | JWT admin | Access token management |
| GET | `/api/v1/runs` | JWT | Run history + stats |

### WebSocket orchestration protocol
```jsonc
// Client connects with Authorization: Bearer <token>
// Client sends:
{ "content": "Summarize last week's transactions" }

// Server streams:
{ "type": "ready", "orchestrator": "finance-agent" }
{ "type": "tool_start", "tool": "agent__data_analyst", "iteration": 1 }
{ "type": "token", "text": "Based on the data..." }
{ "type": "tool_done", "tool": "agent__data_analyst", "duration_ms": 1240 }
{ "type": "done", "run_id": "...", "total_tokens": 1820, "iterations": 2 }
```

---

## Project Structure

```
odin/
├── app/                        # odin-bridge (FastAPI)
│   ├── adapters/               # Agent transport layer
│   │   ├── base.py             # AgentAdapter ABC + AdapterEvent
│   │   ├── omni_ws_adapter.py  # WebSocket → Omni agents
│   │   ├── a2a_adapter.py      # A2A stub (future)
│   │   └── factory.py          # Transport → adapter routing
│   ├── routers/                # API endpoints
│   │   ├── ws_orchestrator.py  # /ws/orchestrate/{name}
│   │   ├── ws_dashboard.py     # /ws/dashboard
│   │   ├── admin_agents.py     # /api/v1/admin/agents
│   │   ├── admin_orchestrators.py
│   │   ├── admin_tokens.py
│   │   └── runs.py             # /api/v1/runs
│   └── services/
│       ├── orchestrator_service.py  # Agentic loop
│       ├── agent_registry.py        # L1+L2 cached agent list
│       ├── token_cache.py           # Bearer token validation
│       ├── rate_limiter.py          # Redis INCR rate limiting
│       ├── run_recorder.py          # Postgres run logging
│       └── dashboard_broadcaster.py # Redis pub/sub events
├── auth_service/               # odin-auth-service (FastAPI)
├── frontend/                   # odin-frontend (Next.js 16)
│   └── src/app/
│       ├── login/              # Login page
│       ├── dashboard/          # Command center
│       ├── agents/             # Agent registry view
│       └── runs/               # Run history
├── postgres/init/              # DB schema auto-applied on first boot
├── redis/config/               # Redis config (AOF, LRU eviction)
├── volumes/                    # Bind-mounted persistent data
│   ├── postgres/pgdata/
│   ├── redis/
│   └── logs/
├── scripts/tests/              # 15-suite test framework
│   ├── run_all_tests.sh        # Full suite runner
│   └── test_01_db.sh … test_15_compose_health.sh
└── docs/                       # Architecture, schema, lessons learned
```

---

## Scalability

Odin is multi-replica from day one:

| State | Where | Replica-safe |
|---|---|---|
| Token cache L1 | In-process per replica | Each replica caches independently |
| Token cache L2 | Redis `odin:session:token:*` TTL 300s | ✓ Shared |
| Rate limiting | Redis INCR `rl:odin:*` | ✓ Shared |
| Agent registry | Redis `odin:agents:registry` + pub/sub | ✓ Shared, invalidated on write |
| Orchestrator config | Redis `odin:orchestrators:{name}` TTL 600s | ✓ Shared |
| Run state | Postgres `odin.runs` | ✓ Shared |
| WS connections | In-process per replica | By design — Traefik sticky sessions |

Start replica 2:
```bash
docker compose --profile replica up -d odin-bridge-2
```

---

## Testing

```bash
# Full suite (all 15 test suites)
bash scripts/tests/run_all_tests.sh

# Live end-to-end (requires admin JWT)
ADMIN_JWT=<token> bash scripts/tests/test_14_e2e_orchestrate.sh

# Individual phase
bash scripts/tests/run_phase7_tests.sh
```

See `docs/tests/TEST_INDEX.md` for the full index and deployment checklist.

---

## Adding an Agent

1. POST to `/api/v1/admin/agents`:
```json
{
  "slug": "my_agent",
  "name": "My Agent",
  "description": "What this agent does — the LLM reads this to decide when to call it",
  "transport": "omni_ws",
  "endpoint_url": "ws://omni-bridge:8500/ws/chat",
  "auth_token_encrypted": "<plaintext — stored encrypted>",
  "timeout_seconds": 30,
  "max_concurrency": 3,
  "enabled": true
}
```

2. Create or update an orchestrator to include the agent's ID in `allowed_agents`.

3. Connect to `ws://localhost:8001/ws/orchestrate/{orchestrator_name}` with a Bearer token and send `{"content": "your goal"}`.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ODIN_DB_PASSWORD` | ✓ | Postgres password |
| `ODIN_SECRET_KEY` | ✓ | Bridge signing key (min 32 chars) |
| `ODIN_JWT_SECRET` | ✓ | Auth service JWT key (min 32 chars) |
| `ANTHROPIC_API_KEY` | ✓ | LLM provider key |
| `ODIN_HOSTNAME` | ✓ | Traefik hostname for bridge |
| `ODIN_UI_HOSTNAME` | — | Traefik hostname for frontend |
| `ODIN_REDIS_PASSWORD` | — | Redis password (optional on private network) |
| `ANTHROPIC_MODEL` | — | Default: `claude-sonnet-4-6` |
| `LOG_LEVEL` | — | Default: `INFO` |

Generate secrets:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## License

© 2026 Avi Cohen. All rights reserved.
