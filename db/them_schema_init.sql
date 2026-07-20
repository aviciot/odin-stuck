--
-- PostgreSQL database dump
--

\restrict MqrmrqGURCURjH2GaZRh9esyVMb36NcdYYSsTHB2iGCNMFATm8jnY6ljKaXddKv

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: them; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA them;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_tokens; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.access_tokens (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    token_hash text NOT NULL,
    label text NOT NULL,
    user_id integer NOT NULL,
    orchestrator_id uuid,
    enabled boolean DEFAULT true NOT NULL,
    expires_at timestamp with time zone,
    last_used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: agents; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.agents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    slug text NOT NULL,
    display_name text NOT NULL,
    description text NOT NULL,
    transport text DEFAULT 'omni_ws'::text NOT NULL,
    endpoint_url text NOT NULL,
    auth_token_encrypted text,
    input_schema jsonb DEFAULT '{"type": "object", "required": ["message"], "properties": {"message": {"type": "string"}}}'::jsonb NOT NULL,
    timeout_seconds integer DEFAULT 120 NOT NULL,
    max_concurrency integer DEFAULT 4 NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    tags text[] DEFAULT '{}'::text[] NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    agent_card jsonb,
    agent_card_url text,
    supports_streaming boolean DEFAULT false NOT NULL,
    supports_push boolean DEFAULT false NOT NULL,
    card_fetched_at timestamp with time zone,
    skills jsonb DEFAULT '[]'::jsonb NOT NULL,
    last_scan_at timestamp with time zone,
    last_scan_result jsonb,
    icon text,
    max_retries integer DEFAULT 2 NOT NULL,
    category text,
    CONSTRAINT agents_slug_check CHECK ((slug ~ '^[a-z0-9_]{1,48}$'::text)),
    CONSTRAINT agents_transport_check CHECK ((transport = 'a2a_async'::text))
);


--
-- Name: app_orchestrators; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.app_orchestrators (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    orchestrator_id uuid,
    name text NOT NULL,
    node_id text NOT NULL,
    kind text DEFAULT 'standard'::text NOT NULL,
    delegatable boolean DEFAULT false NOT NULL,
    display_name text,
    system_prompt text,
    allowed_agent_ids uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    llm_provider text,
    llm_model text,
    llm_api_key_encrypted text,
    llm_base_url text,
    max_iterations integer DEFAULT 10 NOT NULL,
    max_parallel_tools integer DEFAULT 3 NOT NULL,
    rate_limit_rpm integer,
    daily_budget_usd numeric(10,4),
    voice_enabled boolean DEFAULT false NOT NULL,
    transcription_provider character varying(32),
    transcription_model character varying(64),
    transcription_api_key_encrypted text,
    tts_enabled boolean DEFAULT false NOT NULL,
    tts_provider text,
    tts_voice text,
    tts_api_key_encrypted text,
    memory_enabled boolean DEFAULT false NOT NULL,
    summarize_every_n_calls integer DEFAULT 3 NOT NULL,
    memory_raw_fallback_n integer DEFAULT 5 NOT NULL,
    summarizer_provider text,
    summarizer_model text,
    summarizer_api_key_encrypted text,
    edges text[] DEFAULT '{websocket}'::text[] NOT NULL,
    history_window integer DEFAULT 20 NOT NULL,
    budget_tokens integer,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_app_orchestrators_kind CHECK ((kind = ANY (ARRAY['standard'::text, 'router'::text, 'voice'::text]))),
    CONSTRAINT ck_app_orchestrators_name_slug CHECK ((name ~ '^[a-z0-9_-]{1,64}$'::text))
);


--
-- Name: applications; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.applications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    presentation jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    canvas jsonb,
    runtime_config jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: COLUMN applications.runtime_config; Type: COMMENT; Schema: them; Owner: -
--

COMMENT ON COLUMN them.applications.runtime_config IS 'App-level runtime policy: {max_concurrent_sessions, rate_limit_rpm, blocked_tokens[], blocked_user_ids[], session_timeout_minutes}. Enforced by runtime_manager.runtime_gate. {} = unlimited.';


--
-- Name: artifacts; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.artifacts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid NOT NULL,
    context_id uuid NOT NULL,
    artifact_id text NOT NULL,
    name text,
    parts jsonb NOT NULL,
    append_index integer DEFAULT 0 NOT NULL,
    last_chunk boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.audit_logs (
    id bigint NOT NULL,
    user_id integer,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: them; Owner: -
--

CREATE SEQUENCE them.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: them; Owner: -
--

ALTER SEQUENCE them.audit_logs_id_seq OWNED BY them.audit_logs.id;


--
-- Name: config; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.config (
    config_key text NOT NULL,
    config_value jsonb NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: entry_points; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.entry_points (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    slug text NOT NULL,
    entry_point_type text NOT NULL,
    access_policy jsonb DEFAULT '{"mode": "token"}'::jsonb NOT NULL,
    conversation_token_limit integer,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    app_orchestrator_id uuid,
    max_concurrent_sessions integer,
    queue_timeout_seconds integer,
    queue_message text,
    CONSTRAINT entry_points_entry_point_type_check CHECK ((entry_point_type = ANY (ARRAY['websocket'::text, 'sse'::text, 'webrtc'::text, 'a2a'::text, 'voice'::text]))),
    CONSTRAINT entry_points_slug_check CHECK ((slug ~ '^[a-z0-9_-]{1,64}$'::text))
);


--
-- Name: COLUMN entry_points.max_concurrent_sessions; Type: COMMENT; Schema: them; Owner: -
--

COMMENT ON COLUMN them.entry_points.max_concurrent_sessions IS 'Max simultaneous active sessions for this entry point. NULL = unlimited. Enforced by runtime_manager.runtime_gate via atomic Lua EVAL on them:ep:{slug}:sessions.';


--
-- Name: COLUMN entry_points.queue_timeout_seconds; Type: COMMENT; Schema: them; Owner: -
--

COMMENT ON COLUMN them.entry_points.queue_timeout_seconds IS 'Seconds to wait for a slot before rejecting. NULL = immediate reject (no queue).';


--
-- Name: COLUMN entry_points.queue_message; Type: COMMENT; Schema: them; Owner: -
--

COMMENT ON COLUMN them.entry_points.queue_message IS 'Message sent to client while waiting for a slot. NULL = default.';


--
-- Name: llm_providers; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.llm_providers (
    id integer NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    api_key_encrypted text,
    base_url text,
    default_model text NOT NULL,
    model_pricing jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: llm_providers_id_seq; Type: SEQUENCE; Schema: them; Owner: -
--

CREATE SEQUENCE them.llm_providers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_providers_id_seq; Type: SEQUENCE OWNED BY; Schema: them; Owner: -
--

ALTER SEQUENCE them.llm_providers_id_seq OWNED BY them.llm_providers.id;


--
-- Name: middleware_defs; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.middleware_defs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    slug text NOT NULL,
    kind text NOT NULL,
    display_name text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_builtin boolean DEFAULT false NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_mw_defs_kind CHECK ((kind = ANY (ARRAY['guard'::text, 'cache'::text])))
);


--
-- Name: middleware_wirings; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.middleware_wirings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    def_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    config_override jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    node_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: orchestrators; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.orchestrators (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    system_prompt text DEFAULT ''::text NOT NULL,
    allowed_agent_ids uuid[] DEFAULT '{}'::uuid[] NOT NULL,
    llm_provider text,
    llm_model text,
    llm_api_key_encrypted text,
    llm_base_url text,
    max_iterations integer DEFAULT 10 NOT NULL,
    max_parallel_tools integer DEFAULT 4 NOT NULL,
    rate_limit_rpm integer DEFAULT 30 NOT NULL,
    daily_budget_usd numeric(10,4) DEFAULT 0 NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    voice_enabled boolean DEFAULT false NOT NULL,
    transcription_provider character varying(32),
    transcription_model character varying(64),
    transcription_api_key_encrypted text,
    tts_enabled boolean DEFAULT false NOT NULL,
    tts_provider text,
    tts_voice text,
    tts_api_key_encrypted text,
    memory_enabled boolean DEFAULT false NOT NULL,
    summarize_every_n_calls integer DEFAULT 3 NOT NULL,
    memory_raw_fallback_n integer DEFAULT 5 NOT NULL,
    summarizer_provider text,
    summarizer_model text,
    summarizer_api_key_encrypted text,
    edges text[] DEFAULT ARRAY['websocket'::text] NOT NULL,
    budget_tokens integer,
    history_window integer DEFAULT 20 NOT NULL,
    delegatable boolean DEFAULT false NOT NULL
);


--
-- Name: run_steps; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.run_steps (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid NOT NULL,
    iteration integer NOT NULL,
    agent_id uuid,
    agent_slug text NOT NULL,
    tool_call_id text NOT NULL,
    input jsonb NOT NULL,
    output text,
    status text DEFAULT 'pending'::text NOT NULL,
    error text,
    latency_ms integer,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    CONSTRAINT run_steps_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'running'::text, 'completed'::text, 'failed'::text, 'timeout'::text])))
);


--
-- Name: run_usage; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.run_usage (
    id bigint NOT NULL,
    run_id uuid NOT NULL,
    user_id integer NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    tokens_input integer DEFAULT 0 NOT NULL,
    tokens_output integer DEFAULT 0 NOT NULL,
    cost_usd numeric(12,8) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: run_usage_id_seq; Type: SEQUENCE; Schema: them; Owner: -
--

CREATE SEQUENCE them.run_usage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: run_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: them; Owner: -
--

ALTER SEQUENCE them.run_usage_id_seq OWNED BY them.run_usage.id;


--
-- Name: runs; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    orchestrator_id uuid,
    orchestrator_name text NOT NULL,
    user_id integer NOT NULL,
    session_id uuid NOT NULL,
    goal text NOT NULL,
    status text DEFAULT 'running'::text NOT NULL,
    final_output text,
    error text,
    iterations integer DEFAULT 0 NOT NULL,
    total_tokens_in integer DEFAULT 0 NOT NULL,
    total_tokens_out integer DEFAULT 0 NOT NULL,
    total_cost_usd numeric(12,8) DEFAULT 0 NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    parent_run_id uuid,
    entry_point_slug text,
    CONSTRAINT runs_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'canceled'::text, 'cancelled'::text, 'stopped'::text])))
);


--
-- Name: task_messages; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.task_messages (
    id bigint NOT NULL,
    task_id uuid NOT NULL,
    role text NOT NULL,
    parts jsonb NOT NULL,
    seq integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_messages_role_check CHECK ((role = ANY (ARRAY['user'::text, 'agent'::text, 'system'::text])))
);


--
-- Name: task_messages_id_seq; Type: SEQUENCE; Schema: them; Owner: -
--

CREATE SEQUENCE them.task_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: them; Owner: -
--

ALTER SEQUENCE them.task_messages_id_seq OWNED BY them.task_messages.id;


--
-- Name: tasks; Type: TABLE; Schema: them; Owner: -
--

CREATE TABLE them.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    run_id uuid,
    parent_task_id uuid,
    orchestrator_id uuid,
    agent_id uuid,
    context_id uuid NOT NULL,
    state text DEFAULT 'submitted'::text NOT NULL,
    kind text DEFAULT 'root'::text NOT NULL,
    remote_task_id text,
    push_url text,
    status_message jsonb,
    input_message jsonb DEFAULT '{}'::jsonb NOT NULL,
    budget_tokens integer,
    deadline timestamp with time zone,
    max_depth integer DEFAULT 5 NOT NULL,
    tokens_used integer DEFAULT 0 NOT NULL,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    user_id integer,
    CONSTRAINT tasks_kind_check CHECK ((kind = ANY (ARRAY['root'::text, 'delegated'::text]))),
    CONSTRAINT tasks_state_check CHECK ((state = ANY (ARRAY['submitted'::text, 'working'::text, 'input-required'::text, 'completed'::text, 'failed'::text, 'canceled'::text, 'rejected'::text])))
);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.audit_logs ALTER COLUMN id SET DEFAULT nextval('them.audit_logs_id_seq'::regclass);


--
-- Name: llm_providers id; Type: DEFAULT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.llm_providers ALTER COLUMN id SET DEFAULT nextval('them.llm_providers_id_seq'::regclass);


--
-- Name: run_usage id; Type: DEFAULT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_usage ALTER COLUMN id SET DEFAULT nextval('them.run_usage_id_seq'::regclass);


--
-- Name: task_messages id; Type: DEFAULT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.task_messages ALTER COLUMN id SET DEFAULT nextval('them.task_messages_id_seq'::regclass);


--
-- Name: access_tokens access_tokens_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.access_tokens
    ADD CONSTRAINT access_tokens_pkey PRIMARY KEY (id);


--
-- Name: access_tokens access_tokens_token_hash_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.access_tokens
    ADD CONSTRAINT access_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: agents agents_slug_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.agents
    ADD CONSTRAINT agents_slug_key UNIQUE (slug);


--
-- Name: app_orchestrators app_orchestrators_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.app_orchestrators
    ADD CONSTRAINT app_orchestrators_pkey PRIMARY KEY (id);


--
-- Name: applications applications_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.applications
    ADD CONSTRAINT applications_pkey PRIMARY KEY (id);


--
-- Name: artifacts artifacts_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.artifacts
    ADD CONSTRAINT artifacts_pkey PRIMARY KEY (id);


--
-- Name: artifacts artifacts_task_id_artifact_id_append_index_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.artifacts
    ADD CONSTRAINT artifacts_task_id_artifact_id_append_index_key UNIQUE (task_id, artifact_id, append_index);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (config_key);


--
-- Name: entry_points entry_points_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.entry_points
    ADD CONSTRAINT entry_points_pkey PRIMARY KEY (id);


--
-- Name: entry_points entry_points_slug_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.entry_points
    ADD CONSTRAINT entry_points_slug_key UNIQUE (slug);


--
-- Name: llm_providers llm_providers_name_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.llm_providers
    ADD CONSTRAINT llm_providers_name_key UNIQUE (name);


--
-- Name: llm_providers llm_providers_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.llm_providers
    ADD CONSTRAINT llm_providers_pkey PRIMARY KEY (id);


--
-- Name: middleware_defs middleware_defs_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_defs
    ADD CONSTRAINT middleware_defs_pkey PRIMARY KEY (id);


--
-- Name: middleware_defs middleware_defs_slug_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_defs
    ADD CONSTRAINT middleware_defs_slug_key UNIQUE (slug);


--
-- Name: middleware_wirings middleware_wirings_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_wirings
    ADD CONSTRAINT middleware_wirings_pkey PRIMARY KEY (id);


--
-- Name: orchestrators orchestrators_name_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.orchestrators
    ADD CONSTRAINT orchestrators_name_key UNIQUE (name);


--
-- Name: orchestrators orchestrators_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.orchestrators
    ADD CONSTRAINT orchestrators_pkey PRIMARY KEY (id);


--
-- Name: run_steps run_steps_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_steps
    ADD CONSTRAINT run_steps_pkey PRIMARY KEY (id);


--
-- Name: run_usage run_usage_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_usage
    ADD CONSTRAINT run_usage_pkey PRIMARY KEY (id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (id);


--
-- Name: task_messages task_messages_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.task_messages
    ADD CONSTRAINT task_messages_pkey PRIMARY KEY (id);


--
-- Name: task_messages task_messages_task_id_seq_key; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.task_messages
    ADD CONSTRAINT task_messages_task_id_seq_key UNIQUE (task_id, seq);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: app_orchestrators uq_app_orchestrators_name; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.app_orchestrators
    ADD CONSTRAINT uq_app_orchestrators_name UNIQUE (name);


--
-- Name: middleware_wirings uq_mw_wiring_app_agent_pos; Type: CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_wirings
    ADD CONSTRAINT uq_mw_wiring_app_agent_pos UNIQUE (application_id, agent_id, "position");


--
-- Name: idx_access_tokens_hash; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_access_tokens_hash ON them.access_tokens USING btree (token_hash);


--
-- Name: idx_access_tokens_user; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_access_tokens_user ON them.access_tokens USING btree (user_id);


--
-- Name: idx_agents_enabled; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_agents_enabled ON them.agents USING btree (enabled);


--
-- Name: idx_agents_slug; Type: INDEX; Schema: them; Owner: -
--

CREATE UNIQUE INDEX idx_agents_slug ON them.agents USING btree (slug);


--
-- Name: idx_app_orchestrators_application_id; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_app_orchestrators_application_id ON them.app_orchestrators USING btree (application_id);


--
-- Name: idx_app_orchestrators_name; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_app_orchestrators_name ON them.app_orchestrators USING btree (name);


--
-- Name: idx_artifacts_ctx; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_artifacts_ctx ON them.artifacts USING btree (context_id, created_at);


--
-- Name: idx_artifacts_task; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_artifacts_task ON them.artifacts USING btree (task_id);


--
-- Name: idx_audit_created; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_audit_created ON them.audit_logs USING btree (created_at DESC);


--
-- Name: idx_entry_points_app_orchestrator_id; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_entry_points_app_orchestrator_id ON them.entry_points USING btree (app_orchestrator_id);


--
-- Name: idx_entry_points_application_id; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_entry_points_application_id ON them.entry_points USING btree (application_id);


--
-- Name: idx_entry_points_slug; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_entry_points_slug ON them.entry_points USING btree (slug);


--
-- Name: idx_mw_defs_kind; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_mw_defs_kind ON them.middleware_defs USING btree (kind);


--
-- Name: idx_mw_wirings_app_agent; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_mw_wirings_app_agent ON them.middleware_wirings USING btree (application_id, agent_id);


--
-- Name: idx_run_steps_agent; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_run_steps_agent ON them.run_steps USING btree (agent_id);


--
-- Name: idx_run_steps_run; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_run_steps_run ON them.run_steps USING btree (run_id, iteration);


--
-- Name: idx_run_usage_run; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_run_usage_run ON them.run_usage USING btree (run_id);


--
-- Name: idx_run_usage_user_created; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_run_usage_user_created ON them.run_usage USING btree (user_id, created_at);


--
-- Name: idx_runs_entry_point_slug; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_runs_entry_point_slug ON them.runs USING btree (entry_point_slug);


--
-- Name: idx_runs_orchestrator; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_runs_orchestrator ON them.runs USING btree (orchestrator_id, started_at DESC);


--
-- Name: idx_runs_parent_run_id; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_runs_parent_run_id ON them.runs USING btree (parent_run_id);


--
-- Name: idx_runs_status; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_runs_status ON them.runs USING btree (status);


--
-- Name: idx_runs_user_started; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_runs_user_started ON them.runs USING btree (user_id, started_at DESC);


--
-- Name: idx_task_messages; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_task_messages ON them.task_messages USING btree (task_id, seq);


--
-- Name: idx_tasks_context; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_context ON them.tasks USING btree (context_id, created_at);


--
-- Name: idx_tasks_parent; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_parent ON them.tasks USING btree (parent_task_id);


--
-- Name: idx_tasks_remote; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_remote ON them.tasks USING btree (remote_task_id);


--
-- Name: idx_tasks_run; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_run ON them.tasks USING btree (run_id);


--
-- Name: idx_tasks_state; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_state ON them.tasks USING btree (state) WHERE (state = ANY (ARRAY['submitted'::text, 'working'::text, 'input-required'::text]));


--
-- Name: idx_tasks_user_id; Type: INDEX; Schema: them; Owner: -
--

CREATE INDEX idx_tasks_user_id ON them.tasks USING btree (user_id);


--
-- Name: uq_app_orch_app_node; Type: INDEX; Schema: them; Owner: -
--

CREATE UNIQUE INDEX uq_app_orch_app_node ON them.app_orchestrators USING btree (application_id, node_id);


--
-- Name: uq_mw_wiring_app_node; Type: INDEX; Schema: them; Owner: -
--

CREATE UNIQUE INDEX uq_mw_wiring_app_node ON them.middleware_wirings USING btree (application_id, node_id) WHERE ((node_id IS NOT NULL) AND (node_id <> ''::text));


--
-- Name: app_orchestrators app_orchestrators_application_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.app_orchestrators
    ADD CONSTRAINT app_orchestrators_application_id_fkey FOREIGN KEY (application_id) REFERENCES them.applications(id) ON DELETE CASCADE;


--
-- Name: artifacts artifacts_task_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.artifacts
    ADD CONSTRAINT artifacts_task_id_fkey FOREIGN KEY (task_id) REFERENCES them.tasks(id) ON DELETE CASCADE;


--
-- Name: entry_points entry_points_app_orchestrator_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.entry_points
    ADD CONSTRAINT entry_points_app_orchestrator_id_fkey FOREIGN KEY (app_orchestrator_id) REFERENCES them.app_orchestrators(id) ON DELETE CASCADE;


--
-- Name: entry_points entry_points_application_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.entry_points
    ADD CONSTRAINT entry_points_application_id_fkey FOREIGN KEY (application_id) REFERENCES them.applications(id) ON DELETE CASCADE;


--
-- Name: middleware_wirings middleware_wirings_agent_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_wirings
    ADD CONSTRAINT middleware_wirings_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES them.agents(id) ON DELETE CASCADE;


--
-- Name: middleware_wirings middleware_wirings_application_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_wirings
    ADD CONSTRAINT middleware_wirings_application_id_fkey FOREIGN KEY (application_id) REFERENCES them.applications(id) ON DELETE CASCADE;


--
-- Name: middleware_wirings middleware_wirings_def_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.middleware_wirings
    ADD CONSTRAINT middleware_wirings_def_id_fkey FOREIGN KEY (def_id) REFERENCES them.middleware_defs(id) ON DELETE RESTRICT;


--
-- Name: run_steps run_steps_agent_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_steps
    ADD CONSTRAINT run_steps_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES them.agents(id) ON DELETE SET NULL;


--
-- Name: run_steps run_steps_run_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_steps
    ADD CONSTRAINT run_steps_run_id_fkey FOREIGN KEY (run_id) REFERENCES them.runs(id) ON DELETE CASCADE;


--
-- Name: run_usage run_usage_run_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.run_usage
    ADD CONSTRAINT run_usage_run_id_fkey FOREIGN KEY (run_id) REFERENCES them.runs(id) ON DELETE CASCADE;


--
-- Name: runs runs_parent_run_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.runs
    ADD CONSTRAINT runs_parent_run_id_fkey FOREIGN KEY (parent_run_id) REFERENCES them.runs(id) ON DELETE SET NULL;


--
-- Name: task_messages task_messages_task_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.task_messages
    ADD CONSTRAINT task_messages_task_id_fkey FOREIGN KEY (task_id) REFERENCES them.tasks(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.tasks
    ADD CONSTRAINT tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES them.agents(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.tasks
    ADD CONSTRAINT tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES them.tasks(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_run_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.tasks
    ADD CONSTRAINT tasks_run_id_fkey FOREIGN KEY (run_id) REFERENCES them.runs(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: them; Owner: -
--

ALTER TABLE ONLY them.tasks
    ADD CONSTRAINT tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict MqrmrqGURCURjH2GaZRh9esyVMb36NcdYYSsTHB2iGCNMFATm8jnY6ljKaXddKv

