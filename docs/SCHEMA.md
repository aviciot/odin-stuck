# the-M Database Schema
# Last updated: 2026-07-07
# Source of truth: db/001_schema.sql + db/003_phase8.sql + db/004_phase9.sql

Schema: `them` (owned by them-bridge)
Auth schema: `auth_service` (owned by them-auth-service — never touch from bridge; use auth_client.py)

> **Note:** table headers below say `odin.*` — this is a doc lag; all tables live in `them.*` schema.

## odin.llm_providers
LLM provider credentials and config. Encrypted API keys via crypto.py.
| Column | Type | Purpose |
|---|---|---|
| id | SERIAL PK | |
| name | TEXT UNIQUE | provider slug: "anthropic", "openai" |
| display_name | TEXT | UI label |
| api_key_encrypted | TEXT | `enc:` Fernet ciphertext |
| base_url | TEXT | for openai_compat providers |
| default_model | TEXT | e.g. "claude-sonnet-4-6" |
| model_pricing | JSONB | `{model: {input: float, output: float}}` per million tokens |
| enabled | BOOL | |

## odin.config
Key→JSONB config store. Key rows: `llm_routing`.
| Column | Type | Purpose |
|---|---|---|
| config_key | TEXT PK | e.g. "llm_routing" |
| config_value | JSONB | e.g. `{"provider":"anthropic","model":"claude-sonnet-4-6"}` |

## odin.agents ⭐
The agent registry. Each row = one LLM tool `agent__<slug>`.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| slug | TEXT UNIQUE | `^[a-z0-9_]{1,48}$` — used in tool name |
| display_name | TEXT | UI label |
| description | TEXT | **LLM tool description** — critical for routing |
| transport | TEXT | `omni_ws` or `a2a` |
| endpoint_url | TEXT | WebSocket URL for the agent |
| auth_token_encrypted | TEXT | `enc:` bearer token sent to agent |
| input_schema | JSONB | JSON Schema for tool input |
| timeout_seconds | INT | per-call timeout |
| max_concurrency | INT | max parallel calls to this agent |
| enabled | BOOL | |
| tags | TEXT[] | grouping/filtering |

## odin.orchestrators ⭐
Named orchestrator configs. One row per WS endpoint `/ws/orchestrate/{name}`.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| name | TEXT UNIQUE | in URL path |
| display_name | TEXT | UI label |
| system_prompt | TEXT | LLM system prompt |
| allowed_agent_ids | UUID[] | empty = all enabled agents |
| llm_provider | TEXT | NULL = use odin.config['llm_routing'] |
| llm_model | TEXT | NULL = use default |
| max_iterations | INT | agentic loop bound |
| max_parallel_tools | INT | concurrent agent calls per iteration |
| rate_limit_rpm | INT | per-user rate limit |
| daily_budget_usd | NUMERIC | 0 = unlimited |
| enabled | BOOL | |
| voice_enabled | BOOL | enable STT transcription |
| transcription_provider | TEXT | e.g. "openai", "groq" |
| transcription_model | TEXT | e.g. "whisper-1" |
| transcription_api_key_encrypted | TEXT | optional override |
| tts_enabled | BOOL | enable text-to-speech |
| tts_provider | TEXT | e.g. "openai" |
| tts_voice | TEXT | e.g. "nova" |
| tts_api_key_encrypted | TEXT | optional override |
| memory_enabled | BOOL | enable context summarization (Phase 8.4) |
| summarize_every_n_calls | INT | trigger summary after N agent calls (default 3) |
| memory_raw_fallback_n | INT | raw artifact fallback count (default 5) |
| summarizer_provider | TEXT | NULL = env default (anthropic/haiku) |
| summarizer_model | TEXT | NULL = env default |
| summarizer_api_key_encrypted | TEXT | optional key override for summarizer |

## odin.access_tokens
Opaque bearer tokens for WS orchestrator access. Token stored as SHA-256 hash.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| token_hash | TEXT UNIQUE | SHA-256 hex of plaintext token |
| label | TEXT | human label |
| user_id | INT | auth_service user ID |
| orchestrator_id | UUID FK→orchestrators | NULL = any orchestrator |
| enabled | BOOL | |
| expires_at | TIMESTAMPTZ | NULL = no expiry |
| last_used_at | TIMESTAMPTZ | updated on each use |

## odin.runs ⭐
One row per orchestrator session (user goal → final answer).
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| orchestrator_id | UUID FK | |
| orchestrator_name | TEXT | denormalized for fast queries |
| user_id | INT | |
| session_id | UUID | WS connection session |
| goal | TEXT | user's input |
| status | TEXT | running/completed/failed/cancelled |
| final_output | TEXT | assembled final answer |
| iterations | INT | actual iterations used |
| total_tokens_in/out | INT | aggregate across all LLM calls |
| total_cost_usd | NUMERIC | aggregate cost |

## odin.run_steps
One row per agent (tool) invocation within a run.
| Column | Type | Purpose |
|---|---|---|
| run_id | UUID FK | parent run |
| iteration | INT | which loop iteration |
| agent_slug | TEXT | which agent was called |
| tool_call_id | TEXT | LLM-provided ID |
| input | JSONB | tool input arguments |
| output | TEXT | agent response |
| status | TEXT | pending/running/completed/failed/timeout |
| latency_ms | INT | adapter round-trip time |

## odin.run_usage
Per-LLM-call token and cost tracking.

## odin.audit_logs
Admin actions: agent/orchestrator/token CRUD.

---

## them.tasks ⭐ (A2A Phase 3+)
Durable task graph. One row per A2A task (root or child). State machine: `submitted → working → completed/failed/canceled/rejected`.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| run_id | UUID FK→runs | NULL for inbound A2A tasks |
| parent_task_id | UUID FK→tasks | for sub-task chains |
| orchestrator_id | UUID FK→orchestrators | which orchestrator owns this task |
| agent_id | UUID FK→agents | set for child tasks |
| context_id | UUID | shared context across tasks in one conversation |
| state | TEXT | `submitted/working/input-required/completed/failed/canceled/rejected` |
| kind | TEXT | `root` or `subtask` |
| input_message | JSONB | A2A message parts |
| status_message | JSONB | agent status message on failure |
| remote_task_id | TEXT | task ID on the child A2A agent |
| error | TEXT | error string on failure |
| budget_tokens | INT | token budget for this task |
| tokens_used | INT | running total |
| deadline | TIMESTAMPTZ | reaper collects hung tasks past this (Phase 9: default +30 min) |
| max_depth | INT | recursion depth limit |
| **user_id** | INT FK→auth_service.users | task owner — NULL for legacy tasks (Phase 9) |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

## them.artifacts (A2A Phase 3+)
Output artifacts produced by agent tasks.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| task_id | UUID FK→tasks | producing task |
| context_id | UUID | inherited from task (for cross-context queries) |
| artifact_id | TEXT | agent-assigned artifact identifier |
| name | TEXT | human label |
| parts | JSONB | A2A part list `[{kind, text/data/...}]` |
| append_index | INT | chunk ordering for streaming artifacts |
| last_chunk | BOOL | true = final chunk |
| created_at | TIMESTAMPTZ | |

## them.applications ⭐ (Phase 9)
User-composable agentic applications. Each row is one deployable entry point bound to an orchestrator.
| Column | Type | Purpose |
|---|---|---|
| id | UUID PK | |
| name | TEXT | display name |
| slug | TEXT UNIQUE | URL-safe ID `^[a-z0-9_-]{1,64}$` |
| entry_point_type | TEXT | `websocket_chat` / `rest` / `voice` / `webrtc` |
| orchestrator_id | UUID FK→orchestrators | target orchestrator (cascade delete) |
| access_policy | JSONB | `{"mode":"token"}` or `{"mode":"public"}` |
| presentation | JSONB | UI metadata (title, theme, icon, etc.) |
| enabled | BOOL | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
