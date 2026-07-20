--
-- PostgreSQL database dump
--

\restrict 0hM9icvm3huh5TokXnBPyGIkf54GkFiOzGK2Snk1NoavAOw5sQLNTiuiKXpma6F

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
-- Name: auth_service; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA auth_service;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_audit; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.auth_audit (
    id integer NOT NULL,
    user_id integer,
    username character varying(255),
    action character varying(100) NOT NULL,
    status character varying(50) NOT NULL,
    ip_address character varying(45),
    user_agent text,
    details text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: auth_audit_id_seq; Type: SEQUENCE; Schema: auth_service; Owner: -
--

CREATE SEQUENCE auth_service.auth_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: auth_service; Owner: -
--

ALTER SEQUENCE auth_service.auth_audit_id_seq OWNED BY auth_service.auth_audit.id;


--
-- Name: blacklisted_tokens; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.blacklisted_tokens (
    token_hash character varying(255) NOT NULL,
    blacklisted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamp without time zone NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    mcp_access text[] DEFAULT '{}'::text[],
    tool_restrictions jsonb DEFAULT '{}'::jsonb,
    dashboard_access character varying(20) DEFAULT 'none'::character varying,
    rate_limit integer DEFAULT 1000,
    cost_limit_daily numeric(10,2) DEFAULT 100.00,
    token_expiry integer DEFAULT 3600,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: auth_service; Owner: -
--

CREATE SEQUENCE auth_service.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: auth_service; Owner: -
--

ALTER SEQUENCE auth_service.roles_id_seq OWNED BY auth_service.roles.id;


--
-- Name: team_members; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.team_members (
    team_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(50) DEFAULT 'member'::character varying,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: teams; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.teams (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    mcp_access text[] DEFAULT '{}'::text[],
    resource_access jsonb DEFAULT '{}'::jsonb,
    team_rate_limit integer,
    team_cost_limit numeric(10,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: auth_service; Owner: -
--

CREATE SEQUENCE auth_service.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: auth_service; Owner: -
--

ALTER SEQUENCE auth_service.teams_id_seq OWNED BY auth_service.teams.id;


--
-- Name: user_overrides; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.user_overrides (
    user_id integer NOT NULL,
    mcp_restrictions text[] DEFAULT '{}'::text[],
    tool_restrictions jsonb DEFAULT '{}'::jsonb,
    custom_rate_limit integer,
    custom_cost_limit numeric(10,2),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: user_sessions; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.user_sessions (
    id integer NOT NULL,
    user_id integer,
    access_token_hash character varying(255) NOT NULL,
    refresh_token_hash character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: user_sessions_id_seq; Type: SEQUENCE; Schema: auth_service; Owner: -
--

CREATE SEQUENCE auth_service.user_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: auth_service; Owner: -
--

ALTER SEQUENCE auth_service.user_sessions_id_seq OWNED BY auth_service.user_sessions.id;


--
-- Name: users; Type: TABLE; Schema: auth_service; Owner: -
--

CREATE TABLE auth_service.users (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(255),
    role_id integer,
    password_hash character varying(255),
    api_key_hash character varying(255),
    active boolean DEFAULT true NOT NULL,
    rate_limit_override integer,
    last_login_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: auth_service; Owner: -
--

CREATE SEQUENCE auth_service.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: auth_service; Owner: -
--

ALTER SEQUENCE auth_service.users_id_seq OWNED BY auth_service.users.id;


--
-- Name: auth_audit id; Type: DEFAULT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.auth_audit ALTER COLUMN id SET DEFAULT nextval('auth_service.auth_audit_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.roles ALTER COLUMN id SET DEFAULT nextval('auth_service.roles_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.teams ALTER COLUMN id SET DEFAULT nextval('auth_service.teams_id_seq'::regclass);


--
-- Name: user_sessions id; Type: DEFAULT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_sessions ALTER COLUMN id SET DEFAULT nextval('auth_service.user_sessions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users ALTER COLUMN id SET DEFAULT nextval('auth_service.users_id_seq'::regclass);


--
-- Name: auth_audit auth_audit_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.auth_audit
    ADD CONSTRAINT auth_audit_pkey PRIMARY KEY (id);


--
-- Name: blacklisted_tokens blacklisted_tokens_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.blacklisted_tokens
    ADD CONSTRAINT blacklisted_tokens_pkey PRIMARY KEY (token_hash);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (team_id, user_id);


--
-- Name: teams teams_name_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.teams
    ADD CONSTRAINT teams_name_key UNIQUE (name);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: user_overrides user_overrides_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_overrides
    ADD CONSTRAINT user_overrides_pkey PRIMARY KEY (user_id);


--
-- Name: user_sessions user_sessions_access_token_hash_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_sessions
    ADD CONSTRAINT user_sessions_access_token_hash_key UNIQUE (access_token_hash);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_refresh_token_hash_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_sessions
    ADD CONSTRAINT user_sessions_refresh_token_hash_key UNIQUE (refresh_token_hash);


--
-- Name: users users_api_key_hash_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users
    ADD CONSTRAINT users_api_key_hash_key UNIQUE (api_key_hash);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_auth_audit_created_at; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_auth_audit_created_at ON auth_service.auth_audit USING btree (created_at);


--
-- Name: idx_auth_audit_user_id; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_auth_audit_user_id ON auth_service.auth_audit USING btree (user_id);


--
-- Name: idx_blacklisted_tokens_expires_at; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_blacklisted_tokens_expires_at ON auth_service.blacklisted_tokens USING btree (expires_at);


--
-- Name: idx_user_sessions_expires_at; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_user_sessions_expires_at ON auth_service.user_sessions USING btree (expires_at);


--
-- Name: idx_user_sessions_user_id; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_user_sessions_user_id ON auth_service.user_sessions USING btree (user_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_users_email ON auth_service.users USING btree (email);


--
-- Name: idx_users_role_id; Type: INDEX; Schema: auth_service; Owner: -
--

CREATE INDEX idx_users_role_id ON auth_service.users USING btree (role_id);


--
-- Name: auth_audit auth_audit_user_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.auth_audit
    ADD CONSTRAINT auth_audit_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE SET NULL;


--
-- Name: team_members team_members_team_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.team_members
    ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES auth_service.teams(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_user_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.team_members
    ADD CONSTRAINT team_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE CASCADE;


--
-- Name: user_overrides user_overrides_user_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_overrides
    ADD CONSTRAINT user_overrides_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_service.users(id) ON DELETE CASCADE;


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: auth_service; Owner: -
--

ALTER TABLE ONLY auth_service.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES auth_service.roles(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 0hM9icvm3huh5TokXnBPyGIkf54GkFiOzGK2Snk1NoavAOw5sQLNTiuiKXpma6F

