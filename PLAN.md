# the-M — A2A-Native Platform Plan
# Last updated: 2026-07-04
# Status: IN PROGRESS

---

## Goal

Transform the-M from an LLM-tool-loop orchestrator into a fully A2A-native platform:
- **Inbound:** the-M is itself an A2A agent — external systems can delegate tasks to it
- **Outbound:** the-M delegates to child agents via A2A, tracking real task lifecycle
- **Memory:** shared context flows through the task graph, not in-RAM accumulators
- **Governance:** budget envelopes, deadlines, token roll-up enforced at every level
- **Playground:** agent debug panel with memory inspection, task graph, artifact view
- **Tests:** real A2A SDK agents, full integration coverage, stale tests removed

**Rules:**
- No patches or workarounds — rewrite cleanly when the old shape is wrong
- Stable and robust over clever
- Every phase ships independently (no big-bang)
- Update docs/ and README on completion of each phase

---

## Phase Overview

| Phase | Name | Status |
|---|---|---|
| 1 | A2A Server — the-M as an A2A agent | TODO |
| 2 | Task graph — durable first-class tasks | TODO |
| 3 | Durable planner — context from DB, not RAM | TODO |
| 4 | Async delegation — long-running agents, push, governance | TODO |
| 5 | Shared context — memory across task graph | TODO |
| 6 | Playground — agent debug panel | TODO |
| 7 | A2A test agents — real SDK, integration tests | TODO |

---

## Phase 1 — A2A Server: the-M as an A2A Agent

**Goal:** External systems can delegate tasks to the-M via A2A protocol.
Zero changes to the existing orchestration loop — this wraps it.

### What to build

**1a. Agent Card endpoint**
`GET /.well-known/agent-card.json`
- Served by `app/routers/a2a_server.py` (new file)
- Built dynamically: each `orchestrators` row where `a2a_exposed=true` becomes one A2A skill
- Security scheme: Bearer token (existing opaque tokens)
- Capabilities: streaming=true, pushNotifications=false (v1)
- Add column: `them.orchestrators.a2a_exposed BOOLEAN NOT NULL DEFAULT false`

**1b. Inbound A2A JSON-RPC endpoint**
`POST /a2a`
- Methods: `SendMessage`, `GetTask`, `CancelTask`
- `SendMessage` → validate bearer token → load orchestrator → run existing loop → return Task
- Task state machine: submitted → working → completed | failed
- Returns A2A-compliant Task JSON with artifacts containing the final answer
- No schema change for tasks yet (Phase 2) — use ephemeral in-memory task tracking backed by `runs`

**1c. Wire `contextId` through outbound adapter**
- `A2aAdapter._send_message_body()` currently sends no context
- Add `context_id` parameter, set as `params.message.contextId` in the JSON-RPC body
- Backward compatible — existing callers pass `None`

### Files changed
- `app/routers/a2a_server.py` — NEW: Agent Card + inbound JSON-RPC handler
- `app/adapters/a2a_adapter.py` — add `context_id` to `_send_message_body`
- `app/main.py` — wire new router
- `db/001_schema.sql` — add `a2a_exposed` column to orchestrators
- `app/models.py` — add `a2a_exposed` field to Orchestrator model

### Tests
- New test: `test_16_a2a_server.py` — GET agent-card returns valid JSON, POST SendMessage returns Task

---

## Phase 2 — Task Graph: Durable First-Class Tasks

**Goal:** Every orchestration run is backed by a durable Task in Postgres.
Tasks survive disconnects, form a parent→child graph, carry budget envelopes.

### Schema additions (db/001_schema.sql)

```sql
CREATE TABLE them.tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES them.runs(id) ON DELETE SET NULL,
    parent_task_id  UUID REFERENCES them.tasks(id) ON DELETE CASCADE,
    orchestrator_id UUID REFERENCES them.orchestrators(id),
    agent_id        UUID REFERENCES them.agents(id),
    context_id      UUID NOT NULL,
    state           TEXT NOT NULL DEFAULT 'submitted'
                    CHECK (state IN ('submitted','working','input-required',
                                     'completed','failed','canceled','rejected')),
    kind            TEXT NOT NULL DEFAULT 'root'
                    CHECK (kind IN ('root','delegated')),
    remote_task_id  TEXT,
    push_url        TEXT,
    status_message  JSONB,
    input_message   JSONB NOT NULL,
    budget_tokens   INTEGER,
    deadline        TIMESTAMPTZ,
    max_depth       INTEGER NOT NULL DEFAULT 5,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE them.artifacts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       UUID NOT NULL REFERENCES them.tasks(id) ON DELETE CASCADE,
    context_id    UUID NOT NULL,
    artifact_id   TEXT NOT NULL,
    name          TEXT,
    parts         JSONB NOT NULL,
    append_index  INTEGER NOT NULL DEFAULT 0,
    last_chunk    BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, artifact_id, append_index)
);

CREATE TABLE them.task_messages (
    id          BIGSERIAL PRIMARY KEY,
    task_id     UUID NOT NULL REFERENCES them.tasks(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user','agent','system')),
    parts       JSONB NOT NULL,
    seq         INTEGER NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, seq)
);

-- Indexes
CREATE INDEX idx_tasks_context    ON them.tasks(context_id, created_at);
CREATE INDEX idx_tasks_parent     ON them.tasks(parent_task_id);
CREATE INDEX idx_tasks_state      ON them.tasks(state)
    WHERE state IN ('submitted','working','input-required');
CREATE INDEX idx_tasks_remote     ON them.tasks(remote_task_id);
CREATE INDEX idx_artifacts_ctx    ON them.artifacts(context_id, created_at);
CREATE INDEX idx_artifacts_task   ON them.artifacts(task_id);
CREATE INDEX idx_task_messages    ON them.task_messages(task_id, seq);
```

**Extend `them.agents`:**
```sql
ALTER TABLE them.agents
    ADD COLUMN agent_card         JSONB,
    ADD COLUMN agent_card_url     TEXT,
    ADD COLUMN supports_streaming BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN supports_push      BOOLEAN NOT NULL DEFAULT false;
```

### New service: `app/services/task_store.py`
- `create_task(...)` → INSERT, enforce state machine
- `transition(task_id, new_state, ...)` → UPDATE with guard (rejects illegal transitions)
- `get_task(task_id)` → SELECT
- `record_artifact(task_id, context_id, artifact_id, parts, ...)` → INSERT into artifacts
- `record_message(task_id, role, parts)` → INSERT into task_messages
- Publishes Redis `them:tasks:{id}:events` on every transition
- All methods async, all errors caught + logged (same pattern as run_recorder.py)

### Phase 1 update
- `a2a_server.py` `SendMessage` now creates a real `them.tasks` row
- Returns `task.id` as the A2A task id
- `GetTask` reads from `them.tasks`

### Files changed
- `db/001_schema.sql` — 3 new tables + agent columns + indexes
- `app/models.py` — Task, Artifact, TaskMessage ORM models + Agent extensions
- `app/services/task_store.py` — NEW: task CRUD + state machine
- `app/services/run_recorder.py` — extend to also write a `tasks` row per run (shadow write)
- `app/routers/a2a_server.py` — wire to real task_store

### Tests
- New test: `test_17_task_store.py` — structural: state machine guards, create/transition/artifact
- Update test_01 to check new tables exist in schema

---

## Phase 3 — Durable Planner: Context from DB, Not RAM

**Goal:** The orchestration loop rebuilds LLM context from the task store instead of
an in-RAM `messages` list. Runs survive disconnects. WS becomes a subscriber.

### The core change

**Current (orchestrator_service.py):**
```python
messages = provider.init_messages(user_goal)          # in-RAM list
for iteration in range(max_iterations):
    async for event in provider.stream_call(messages, tools):
        ...
    messages = provider.append_assistant_response(messages, ...)
    messages = provider.append_tool_results(messages, ...)
```

**New (task_runner.py):**
```python
async def run(root_task_id: UUID, db, redis):
    task = await task_store.get_task(root_task_id)
    orchestrator = await _load_orchestrator(task.orchestrator_id, db)
    
    for iteration in range(orchestrator.max_iterations):
        # Rebuild from DB — this is what makes it resumable
        messages = await _build_messages_from_store(task.context_id, db)
        
        async for event in provider.stream_call(messages, tools):
            if event.type == "token":
                await _publish(task.id, event)         # Redis → WS subscribers
            elif event.type == "tool_calls":
                child_tasks = await _delegate(task, event.tool_calls, db)
                await _wait_for_children(child_tasks)
            elif event.type == "done":
                await task_store.record_artifact(task.id, ...)
                await task_store.transition(task.id, "completed")
                break
```

### New file: `app/services/task_runner.py`
Replaces the body of `orchestrator_service.run_orchestrator`. Clean rewrite.
- `run(root_task_id, publish_fn, db, redis)` — main entry, replaces the generator
- `_build_messages_from_store(context_id, db)` — query task_messages + artifacts by context
- `_delegate(parent_task, tool_calls, db)` — create child task rows, dispatch via adapter
- `_wait_for_children(child_task_ids)` — asyncio.gather for fast agents; suspend for slow
- `_publish(task_id, event)` — Redis publish to `them:tasks:{id}:events`

### WS endpoint becomes a subscriber
`app/routers/ws_orchestrator.py` — rewrite:
1. Auth, load orchestrator (same as today)
2. Create root task via `task_store.create_task()`
3. Launch `task_runner.run(task.id)` as `asyncio.create_task()` — **detached from socket**
4. Subscribe to Redis `them:tasks:{task.id}:events`
5. Relay events to WS client
6. On disconnect: subscription ends, task keeps running

**Flag:** `orchestrators.a2a_exposed` used to gate — orchestrators with this flag use the new path.
All others keep the old `run_orchestrator` path during migration.
Remove flag and delete old path once proven stable.

### Files changed
- `app/services/task_runner.py` — NEW: durable loop
- `app/routers/ws_orchestrator.py` — rewrite as subscriber
- `app/services/orchestrator_service.py` — keep for legacy path during migration, mark deprecated
- `docs/ARCHITECTURE.md` — update loop description

### Tests
- Update test_10 (run recorder) — extend to cover task_store
- Update test_11 (WS orchestrate) — test reconnect scenario
- New test_18 — task survives WS disconnect (structural)

---

## Phase 4 — Async Delegation: Long-Running Agents, Push, Governance

**Goal:** Child agents can run for minutes/hours. Budget enforced. Reaper kills overdue tasks.

### New adapter: `app/adapters/a2a_async_adapter.py`
Transport value: `a2a_async`
- `submit(input, context_id, push_url)` → POST SendMessage, return `remote_task_id` immediately (non-blocking)
- `stream_events(remote_task_id)` → SSE stream if agent supports streaming
- Registers push callback URL in SendMessage params when `agent.supports_push=true`
- Falls back to `GetTask` polling with long configurable deadline (not hardcoded 30s)
- **Preserves full artifact parts array** — no more "first text part wins" truncation
- Yields new `AdapterEvent` types: `task_created`, `artifact`, `status`

### Extended `AdapterEvent` (app/adapters/base.py)
```python
@dataclass
class AdapterEvent:
    type: str   # token | artifact | status | done | error | task_created
    text: str | None = None
    result: str | None = None
    error: str | None = None
    remote_task_id: str | None = None   # on task_created
    state: str | None = None             # on status
    artifact: dict | None = None         # full A2A parts array
    input_required: bool = False
```

### Push webhook: `POST /a2a/push/{task_id}`
- New endpoint in `a2a_server.py`
- Child agent calls this when its task state changes
- Idempotent: `ON CONFLICT DO NOTHING` / state machine guards prevent double-processing
- Looks up child task by `task_id`, updates state, publishes to Redis
- Wakes the parent's `task_runner` via Redis signal

### Governance
**Budget envelope** on `them.tasks`:
- `budget_tokens` — max tokens this task tree may consume (inherited from orchestrator config)
- `deadline` — absolute timestamp (not a timeout offset — survives reconnects)
- `max_depth` — prevents infinite delegation chains
- `tokens_used` — rolls up from children; checked before each planning turn

**Reaper background task** (app/main.py):
- Runs every 60s
- `SELECT * FROM them.tasks WHERE state IN ('working','submitted') AND deadline < now()`
- For each: call `task_store.transition(id, 'failed', error='deadline exceeded')`
- Publish cancellation event, surface error to parent

**Token roll-up:**
- `run_recorder.record_usage()` also increments `them.tasks.tokens_used` for the root task
- Before each planning turn: check `tokens_used >= budget_tokens` → fail gracefully

### Files changed
- `app/adapters/a2a_async_adapter.py` — NEW
- `app/adapters/base.py` — extend AdapterEvent
- `app/adapters/factory.py` — add `a2a_async` branch
- `app/routers/a2a_server.py` — add push webhook endpoint
- `app/main.py` — add reaper background task
- `db/001_schema.sql` — already added budget columns in Phase 2
- `docs/ADAPTERS.md` — document new transport

### Tests
- Update test_07 — cover new AdapterEvent types, a2a_async factory branch
- New test_19 — push webhook idempotency (structural)
- New test_20 — reaper logic (structural)

---

## Phase 5 — Shared Context: Memory Across Task Graph

**Goal:** Agents share context naturally. The-M controls all writes. No separate memory service.

### How it works

When the orchestrator delegates to a child agent:
1. Query `them.artifacts WHERE context_id = $1 ORDER BY created_at` (recent N artifacts)
2. Select relevant ones (recency + size budget)
3. Inline them in the outbound A2A message parts
4. Child agent sees the context; we persist its response as a new artifact

That's the memory read/write cycle. The-M is the sole writer.

### Redis hot cache
Key: `them:ctx:{context_id}:heads`
- Short TTL (300s) — cached list of artifact IDs + previews for active runs
- Invalidated on every `record_artifact()` call
- Falls through to Postgres on miss (same L1/L2 pattern as token_cache)

### New service: `app/services/context_service.py`
- `get_shared_context(context_id, limit, db)` → list of artifacts for a context
- `record_artifact(task_id, context_id, parts, db)` → write artifact + invalidate cache
- Called by `task_runner.py` — never by adapters or external code

### No agent-facing API
Agents receive context inlined in messages. They never call our memory endpoints.

### Redis key added
`them:ctx:{context_id}:heads` — document in `docs/REDIS.md`

### Files changed
- `app/services/context_service.py` — NEW
- `app/services/task_runner.py` — call context_service on delegate + on result
- `docs/REDIS.md` — add `them:ctx:*`
- `docs/ARCHITECTURE.md` — update memory section

### Tests
- New test_21 — context_service: write artifact, read it back, cache invalidation (structural)

---

## Phase 6 — Playground: Agent Debug Panel

**Goal:** Right tray in playground shows per-agent detail with memory inspection,
task graph, artifact viewer, and live status.

### New right tray sections (frontend/src/app/admin/playground/page.tsx)

Replace the current flat trace list with tabbed debug panel:

**Tab 1 — Task Graph**
- Tree view: root task → child tasks
- Each node: agent name, state badge (submitted/working/completed/failed), duration
- Click node → expand to see input/output artifacts

**Tab 2 — Agents**
- Card per agent invoked in this run
- Shows: slug, transport, state, latency, token count
- Button: "Fetch Agent Card" → GET `{agent.endpoint_url}/.well-known/agent-card.json`
  → display skills, capabilities, supported interfaces

**Tab 3 — Artifacts**
- List of all artifacts produced in this run, by task
- Expandable: show full `parts` array (text, file refs, data)
- Filter by agent/task

**Tab 4 — Memory / Context**
- Shows artifacts that were *inlined as context* for each delegation
- "What did this agent know when it was called?"
- Source: the `them:ctx:{context_id}:heads` cache + artifact detail from DB
- New API endpoint: `GET /api/v1/runs/{run_id}/context` → returns context snapshots per delegation

**New button on each agent card:** "Fetch Memories"
- Calls `GET /api/v1/context/{context_id}/artifacts`
- Displays what's stored under this context
- Shows artifact count, sizes, timestamps

### New API endpoints (app/routers/runs.py)
- `GET /api/v1/runs/{run_id}/tasks` — task graph for a run
- `GET /api/v1/runs/{run_id}/artifacts` — artifacts for a run
- `GET /api/v1/context/{context_id}/artifacts` — all artifacts for a context (memory inspector)

### Files changed
- `frontend/src/app/admin/playground/page.tsx` — full UI rewrite of right tray
- `app/routers/runs.py` — 3 new endpoints
- `frontend/src/lib/api.ts` — new API calls

### Tests
- New test_22 — runs/{id}/tasks, runs/{id}/artifacts endpoints return expected shape (live)

---

## Phase 7 — A2A Test Agents: Real SDK, Integration Tests

**Goal:** Spin up 2-3 real A2A agents built on the official Python A2A SDK.
Confirm the platform handles them correctly. Fix anything that breaks.

### Test agents to build (agents/a2a_*/):

**Agent 1: `a2a-echo`** (simple, synchronous)
- Skills: `echo` — returns the input message verbatim
- Transport: A2A, non-streaming, immediate completion
- Tests: basic SendMessage → Task(completed), artifact extraction

**Agent 2: `a2a-slow`** (long-running)
- Skills: `slow_task` — waits 10-60s before completing
- Tests: polling fallback, deadline enforcement, budget governance

**Agent 3: `a2a-stream`** (streaming)
- Skills: `stream_words` — streams a response word by word via SSE
- Advertises `capabilities.streaming=true` in Agent Card
- Tests: A2aAsyncAdapter SSE consumption, artifact assembly from chunks

### Each agent:
- Built with official `a2a-sdk` Python package (latest)
- Runs in Docker, added to `docker-compose.yml` under `profiles: [test-agents]`
- Has its own `/.well-known/agent-card.json`
- Seeded into `them.agents` with `transport=a2a_async`

### New tests replacing stale ones:

**Remove:**
- `test_07_adapter_factory.py` — replace entirely (tests old A2aAdapter assumptions)
- `test_14_e2e_orchestrate.sh` — replace with Python E2E using real A2A agents

**New:**
- `test_07_adapters.py` — factory, AdapterEvent types, a2a + a2a_async + omni_ws
- `test_14_e2e_a2a.py` — full E2E: create token → connect WS → orchestrator calls a2a-echo → verify task + artifact in DB
- `test_23_a2a_slow.py` — E2E: slow agent, verify deadline enforcement
- `test_24_a2a_stream.py` — E2E: streaming agent, verify artifact assembly

### Claude API token usage (from DB)
- Tests retrieve the ANTHROPIC_API_KEY from `them.llm_providers` where `name='anthropic'`
- Each E2E test uses the shortest possible goal ("echo: hello") to minimize token spend
- Tests share a single orchestration run where possible

### Files changed
- `agents/a2a_echo/` — NEW: echo agent
- `agents/a2a_slow/` — NEW: slow agent  
- `agents/a2a_stream/` — NEW: streaming agent
- `docker-compose.yml` — add 3 test agent services under `profiles: [test-agents]`
- `db/002_seed.sql` — seed the 3 A2A test agents
- `scripts/tests/` — remove stale, add new tests
- `scripts/tests/INDEX.md` — update test index
- `docs/STATUS.md` — record test results
- `README.md` — update once all phases complete

---

## What Does NOT Change

| Component | Why |
|---|---|
| `runs` / `run_steps` / `run_usage` | Kept as billing/analytics log. `tasks` links via `run_id`. |
| `OmniWsAdapter` | Fast sync WS agents still work as-is |
| `A2aAdapter` (transport=`a2a`) | Legacy Omni sync path kept for backward compat |
| Token cache L1/L2 pattern | Solid, proven, multi-replica safe |
| Agent registry L1/L2 + pub/sub | Kept, extended with agent_card fetch |
| Auth service (port 8701) | Untouched |
| Rate limiter | Untouched |
| LLM providers | Untouched — LLM is still the planner |

---

## Docs to Update Per Phase

| Phase | Docs |
|---|---|
| 1 | ARCHITECTURE.md (A2A server), ADAPTERS.md (contextId) |
| 2 | SCHEMA.md (3 new tables), ARCHITECTURE.md (task graph) |
| 3 | ARCHITECTURE.md (durable planner loop) |
| 4 | ADAPTERS.md (a2a_async), REDIS.md (no new keys), ARCHITECTURE.md (governance) |
| 5 | REDIS.md (them:ctx:*), ARCHITECTURE.md (memory) |
| 6 | STATUS.md (playground features) |
| 7 | README.md (final update), STATUS.md (test results) |

---

## Progress Tracking

- [x] Phase 1 — A2A Server
- [x] Phase 2 — Task Graph Schema
- [ ] Phase 3 — Durable Planner
- [ ] Phase 4 — Async Delegation + Governance
- [ ] Phase 5 — Shared Context / Memory
- [ ] Phase 6 — Playground Debug Panel
- [ ] Phase 7 — Real A2A Test Agents + Integration Tests
