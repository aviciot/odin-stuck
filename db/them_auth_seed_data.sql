--
-- PostgreSQL database dump
--

\restrict bHvEUciILnhsSiNdhrNeRjd6038OZwL0cf93rbFw6TotKg68EJBSD0b0zSH7X5N

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
-- Data for Name: roles; Type: TABLE DATA; Schema: auth_service; Owner: -
--

COPY auth_service.roles (id, name, description, mcp_access, tool_restrictions, dashboard_access, rate_limit, cost_limit_daily, token_expiry, created_at, updated_at) FROM stdin;
1	super_admin	Full system access	{*}	{}	admin	10000	1000.00	7200	2026-07-06 10:57:14.448949	2026-07-06 10:57:14.448949
2	developer	Developer access	{database_mcp,macgyver_mcp,informatica_mcp}	{"database_mcp": ["analyze_full_sql_context", "compare_query_plans"], "macgyver_mcp": ["*"], "informatica_mcp": ["*"]}	view	5000	100.00	7200	2026-07-06 10:57:14.448949	2026-07-06 10:57:14.448949
3	analyst	Data analyst access	{database_mcp}	{"database_mcp": ["analyze_full_sql_context", "get_top_queries"]}	view	1000	50.00	3600	2026-07-06 10:57:14.448949	2026-07-06 10:57:14.448949
4	viewer	Read-only access	{}	{}	view	100	10.00	3600	2026-07-06 10:57:14.448949	2026-07-06 10:57:14.448949
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: auth_service; Owner: -
--

COPY auth_service.teams (id, name, description, mcp_access, resource_access, team_rate_limit, team_cost_limit, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: auth_service; Owner: -
--

COPY auth_service.users (id, username, name, email, role_id, password_hash, api_key_hash, active, rate_limit_override, last_login_at, created_at, updated_at) FROM stdin;
2	avi	Avi Cohen	avi.cohen@shift4.com	1	$2b$12$oePlJ/q0ncXcv7pM7S7IY.IytHiFztMCcOa1xteo/VjYStx5HOCq6	\N	t	\N	\N	2026-07-06 11:21:48.164831	2026-07-06 11:21:48.164831
1	admin	Administrator	admin@them.local	1	$2b$12$DZUNNIwrBXjGksKxfkg0fOqAlvNn47G6hXJ6cOMxP1Bpfiw/ZzVSK	\N	t	\N	2026-07-18 20:00:27.515209	2026-07-06 11:21:48.164831	2026-07-06 11:21:48.164831
\.


--
-- Data for Name: team_members; Type: TABLE DATA; Schema: auth_service; Owner: -
--

COPY auth_service.team_members (team_id, user_id, role, joined_at) FROM stdin;
\.


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: auth_service; Owner: -
--

SELECT pg_catalog.setval('auth_service.roles_id_seq', 4, true);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: auth_service; Owner: -
--

SELECT pg_catalog.setval('auth_service.teams_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: auth_service; Owner: -
--

SELECT pg_catalog.setval('auth_service.users_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

\unrestrict bHvEUciILnhsSiNdhrNeRjd6038OZwL0cf93rbFw6TotKg68EJBSD0b0zSH7X5N

