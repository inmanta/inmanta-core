--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2 (Ubuntu 16.2-1.pgdg20.04+1)
-- Dumped by pg_dump version 16.2 (Ubuntu 16.2-1.pgdg20.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
--SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auth_method; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.auth_method AS ENUM (
    'database',
    'oidc'
);


--
-- Name: change; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.change AS ENUM (
    'nochange',
    'created',
    'purged',
    'updated'
);


--
-- Name: non_deploying_resource_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.non_deploying_resource_state AS ENUM (
    'unavailable',
    'skipped',
    'dry',
    'deployed',
    'failed',
    'available',
    'cancelled',
    'undefined',
    'skipped_for_undefined',
    'non_compliant'
);


--
-- Name: notificationseverity; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notificationseverity AS ENUM (
    'message',
    'info',
    'success',
    'warning',
    'error'
);


--
-- Name: resource_id_version_pair; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resource_id_version_pair AS (
	resource_id character varying,
	version integer
);


--
-- Name: resourceaction_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resourceaction_type AS ENUM (
    'store',
    'push',
    'pull',
    'deploy',
    'dryrun',
    'getfact',
    'other'
);


--
-- Name: resourcestate; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resourcestate AS ENUM (
    'unavailable',
    'skipped',
    'dry',
    'deployed',
    'failed',
    'deploying',
    'available',
    'cancelled',
    'undefined',
    'skipped_for_undefined',
    'non_compliant'
);


--
-- Name: versionstate; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.versionstate AS ENUM (
    'success',
    'failed',
    'deploying',
    'pending'
);


SET default_tablespace = '';

--SET default_table_access_method = heap;

--
-- Name: agent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent (
    environment uuid NOT NULL,
    name character varying NOT NULL,
    paused boolean DEFAULT false,
    unpause_on_resume boolean
);


--
-- Name: agent_modules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_modules (
    cm_version integer NOT NULL,
    agent_name character varying NOT NULL,
    inmanta_module_name character varying NOT NULL,
    environment uuid NOT NULL
);


--
-- Name: compile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.compile (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    started timestamp with time zone,
    completed timestamp with time zone,
    requested timestamp with time zone,
    metadata jsonb,
    requested_environment_variables jsonb NOT NULL,
    do_export boolean,
    force_update boolean,
    success boolean,
    version integer,
    remote_id uuid,
    handled boolean,
    substitute_compile_id uuid,
    compile_data jsonb,
    partial boolean DEFAULT false,
    removed_resource_sets character varying[] DEFAULT ARRAY[]::character varying[],
    notify_failed_compile boolean,
    failed_compile_message character varying,
    exporter_plugin character varying,
    mergeable_environment_variables jsonb DEFAULT '{}'::jsonb NOT NULL,
    used_environment_variables jsonb,
    soft_delete boolean DEFAULT false NOT NULL,
    links jsonb DEFAULT '{}'::jsonb NOT NULL,
    reinstall_project_and_venv boolean DEFAULT false NOT NULL
);


--
-- Name: configurationmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationmodel (
    version integer NOT NULL,
    environment uuid NOT NULL,
    date timestamp with time zone,
    released boolean DEFAULT false,
    version_info jsonb,
    total integer DEFAULT 0,
    undeployable character varying[] NOT NULL,
    skipped_for_undeployable character varying[] NOT NULL,
    partial_base integer,
    is_suitable_for_partial_compiles boolean NOT NULL,
    pip_config jsonb,
    project_constraints character varying
);


--
-- Name: configurationmodel_modules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationmodel_modules (
    environment uuid NOT NULL,
    cm_version integer NOT NULL,
    inmanta_module_name character varying NOT NULL,
    inmanta_module_version character varying NOT NULL
);


--
-- Name: discoveredresource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discoveredresource (
    environment uuid NOT NULL,
    discovered_resource_id character varying NOT NULL,
    "values" jsonb NOT NULL,
    discovered_at timestamp with time zone NOT NULL,
    discovery_resource_id character varying NOT NULL,
    resource_type character varying NOT NULL,
    resource_id_value character varying NOT NULL,
    agent character varying NOT NULL
);


--
-- Name: dryrun; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dryrun (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    model integer NOT NULL,
    date timestamp with time zone,
    total integer DEFAULT 0,
    todo integer DEFAULT 0,
    resources jsonb DEFAULT '{}'::jsonb
);


--
-- Name: environment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environment (
    id uuid NOT NULL,
    name character varying NOT NULL,
    project uuid NOT NULL,
    repo_url character varying DEFAULT ''::character varying,
    repo_branch character varying DEFAULT ''::character varying,
    settings jsonb DEFAULT '{}'::jsonb,
    last_version integer DEFAULT 0,
    halted boolean DEFAULT false NOT NULL,
    description character varying(255) DEFAULT ''::character varying,
    icon character varying(65535) DEFAULT ''::character varying,
    is_marked_for_deletion boolean DEFAULT false
);


--
-- Name: environmentmetricsgauge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricsgauge (
    environment uuid NOT NULL,
    metric_name character varying NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    count integer NOT NULL,
    category character varying DEFAULT '__None__'::character varying NOT NULL
);


--
-- Name: environmentmetricstimer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.environmentmetricstimer (
    environment uuid NOT NULL,
    metric_name character varying NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    count integer NOT NULL,
    value double precision NOT NULL,
    category character varying DEFAULT '__None__'::character varying NOT NULL
);


--
-- Name: file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file (
    content_hash character varying NOT NULL,
    content bytea NOT NULL
);


--
-- Name: inmanta_module; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmanta_module (
    name character varying NOT NULL,
    version character varying NOT NULL,
    environment uuid NOT NULL,
    requirements character varying[] DEFAULT ARRAY[]::character varying[],
    editable_install boolean
);


--
-- Name: inmanta_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmanta_user (
    id uuid NOT NULL,
    username character varying NOT NULL,
    password_hash character varying NOT NULL,
    auth_method public.auth_method NOT NULL,
    is_admin boolean DEFAULT false NOT NULL
);


--
-- Name: module_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.module_files (
    inmanta_module_name character varying NOT NULL,
    inmanta_module_version character varying NOT NULL,
    environment uuid NOT NULL,
    file_content_hash character varying NOT NULL,
    python_module_name character varying NOT NULL,
    is_byte_code boolean NOT NULL
);


--
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    created timestamp with time zone NOT NULL,
    title character varying NOT NULL,
    message character varying NOT NULL,
    severity public.notificationseverity DEFAULT 'message'::public.notificationseverity,
    uri character varying,
    read boolean DEFAULT false NOT NULL,
    cleared boolean DEFAULT false NOT NULL,
    compile_id uuid
);


--
-- Name: parameter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parameter (
    id uuid NOT NULL,
    name character varying NOT NULL,
    value character varying DEFAULT ''::character varying NOT NULL,
    environment uuid NOT NULL,
    resource_id character varying DEFAULT ''::character varying,
    source character varying NOT NULL,
    updated timestamp with time zone,
    metadata jsonb,
    expires boolean DEFAULT true NOT NULL
);


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id uuid NOT NULL,
    name character varying NOT NULL
);


--
-- Name: report; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report (
    id uuid NOT NULL,
    started timestamp with time zone NOT NULL,
    completed timestamp with time zone,
    command character varying NOT NULL,
    name character varying NOT NULL,
    errstream character varying DEFAULT ''::character varying,
    outstream character varying DEFAULT ''::character varying,
    returncode integer,
    compile uuid NOT NULL
);


--
-- Name: resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource (
    environment uuid NOT NULL,
    resource_id character varying NOT NULL,
    agent character varying NOT NULL,
    attributes jsonb,
    attribute_hash character varying,
    resource_type character varying NOT NULL,
    resource_id_value character varying NOT NULL,
    is_undefined boolean DEFAULT false,
    resource_set uuid NOT NULL
);


--
-- Name: resource_diff; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_diff (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    environment uuid NOT NULL,
    resource_id character varying NOT NULL,
    diff jsonb NOT NULL,
    created timestamp with time zone NOT NULL
);


--
-- Name: resource_persistent_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_persistent_state (
    environment uuid NOT NULL,
    resource_id character varying NOT NULL,
    last_handler_run_at timestamp with time zone,
    last_success timestamp with time zone,
    last_produced_events timestamp with time zone,
    last_deployed_attribute_hash character varying,
    last_deployed_version integer,
    last_non_deploying_status public.non_deploying_resource_state DEFAULT 'available'::public.non_deploying_resource_state NOT NULL,
    resource_type character varying NOT NULL,
    agent character varying NOT NULL,
    resource_id_value character varying NOT NULL,
    current_intent_attribute_hash character varying,
    is_undefined boolean NOT NULL,
    last_handler_run character varying NOT NULL,
    blocked character varying NOT NULL,
    is_deploying boolean DEFAULT false,
    created timestamp with time zone NOT NULL,
    last_handler_run_compliant boolean,
    non_compliant_diff uuid,
    orphaned_after integer
);


--
-- Name: resource_set; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_set (
    environment uuid NOT NULL,
    id uuid NOT NULL,
    name character varying
);


--
-- Name: resource_set_configuration_model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_set_configuration_model (
    environment uuid NOT NULL,
    model integer NOT NULL,
    resource_set uuid NOT NULL
);


--
-- Name: resourceaction; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction (
    action_id uuid NOT NULL,
    action public.resourceaction_type NOT NULL,
    started timestamp with time zone NOT NULL,
    finished timestamp with time zone,
    messages jsonb[],
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    changes jsonb DEFAULT '{}'::jsonb,
    change public.change,
    environment uuid NOT NULL,
    version integer NOT NULL,
    resource_version_ids character varying[] NOT NULL
);


--
-- Name: resourceaction_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resourceaction_resource (
    environment uuid NOT NULL,
    resource_action_id uuid NOT NULL,
    resource_id character varying NOT NULL,
    resource_version integer NOT NULL
);


--
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    id uuid NOT NULL,
    name character varying NOT NULL
);


--
-- Name: role_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_assignment (
    user_id uuid NOT NULL,
    environment uuid NOT NULL,
    role_id uuid NOT NULL
);


--
-- Name: scheduler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scheduler (
    environment uuid NOT NULL,
    last_processed_model_version integer
);


--
-- Name: schedulersession; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedulersession (
    hostname character varying NOT NULL,
    environment uuid NOT NULL,
    first_seen timestamp with time zone,
    expired timestamp with time zone,
    sid uuid NOT NULL
);


--
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    installed_versions integer[]
);


--
-- Name: token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token (
    jti uuid NOT NULL,
    created_by character varying,
    client_types character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL,
    environment uuid,
    issued_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone,
    last_used timestamp with time zone,
    revoked_at timestamp with time zone
);


--
-- Name: unknownparameter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unknownparameter (
    id uuid NOT NULL,
    name character varying NOT NULL,
    environment uuid NOT NULL,
    source character varying NOT NULL,
    resource_id character varying DEFAULT ''::character varying,
    version integer NOT NULL,
    metadata jsonb,
    resolved boolean DEFAULT false
);


--
-- Data for Name: agent; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent (environment, name, paused, unpause_on_resume) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	$__scheduler	f	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	$__scheduler	f	\N
48e192b4-5601-455b-b6af-77f12abbff12	$__scheduler	f	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	internal	f	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	localhost	f	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	internal	f	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	localhost	f	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	agent2	f	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	agent3	f	\N
caa3434d-c318-464e-996c-0dca4526c4cb	agent1	t	t
caa3434d-c318-464e-996c-0dca4526c4cb	$__scheduler	t	t
08bdb3be-1cd1-4c2a-8223-6841bf57a9d1	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
1	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
1	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
1	internal	std	16c22fa4-02d4-4de6-99f9-c4275fbcf00b
1	localhost	fs	16c22fa4-02d4-4de6-99f9-c4275fbcf00b
2	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
2	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
2	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
3	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
3	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
3	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
4	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
4	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
4	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
5	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
5	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
5	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
6	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
6	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
6	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
7	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
7	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
7	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
8	localhost	fs	48a137cb-bcd1-4a08-8daa-39da44bd3669
8	internal	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
8	localhost	std	48a137cb-bcd1-4a08-8daa-39da44bd3669
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
51b8b896-617a-4907-841e-d973293be5b3	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:32:41.096207+02	2026-09-09 10:32:56.939849+02	2026-09-09 10:32:41.065796+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	131f821f-4df4-4db0-ab53-fa9612f40616	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
47f7bf65-e2d2-490a-a936-17ede5ee887e	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	2026-09-09 10:32:57.106546+02	2026-09-09 10:33:12.494425+02	2026-09-09 10:32:57.092755+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ce12ce95-260d-44bf-bd32-0742b05589a9	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f1d14a05-c6b6-4dea-8cbf-aef2171279bc	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:12.711385+02	2026-09-09 10:33:13.687859+02	2026-09-09 10:33:12.698516+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	91be04d8-bc75-4ce3-b22d-f0036bbfe2b1	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
7c8e9c9c-3665-44a0-91f3-405914f8a4fa	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:13.81876+02	2026-09-09 10:33:14.792738+02	2026-09-09 10:33:13.804875+02	{}	{"add_one_resource": "true"}	t	f	t	3	5fa9cc1f-2827-4596-a9af-a59c95f348d0	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
db2cd735-7ca6-414b-9e99-5f43838d6637	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:15.070822+02	2026-09-09 10:33:15.973249+02	2026-09-09 10:33:15.064465+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	bc2ba991-f4f2-485f-8684-336792846b80	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
2a4034a2-2f6f-4b88-9909-032df1633041	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:16.128583+02	2026-09-09 10:33:17.089968+02	2026-09-09 10:33:16.124995+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	7d2d810d-9de0-432e-89c6-ab001b381b21	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6ba5b2d4-846d-4547-8eaf-c0416ce58252	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:17.255038+02	2026-09-09 10:33:30.924974+02	2026-09-09 10:33:17.244106+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	56d8ee8e-ac7f-4d33-9aa3-539f99946c5b	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
86914943-f19b-42bb-a4ba-0edeac4fc228	08bdb3be-1cd1-4c2a-8223-6841bf57a9d1	2026-09-09 10:33:31.907812+02	2026-09-09 10:33:31.913516+02	2026-09-09 10:33:31.894294+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	11110a83-3f83-46fb-94b3-14c6167eccd4	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:32:56.920874+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:31.135041+02	t	\N	3	{}	{}	7	t	\N	\N
1	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	2026-09-09 10:33:12.481537+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:13.679562+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:14.78128+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:15.965198+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:17.080372+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:30.9144+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	caa3434d-c318-464e-996c-0dca4526c4cb	2026-09-09 10:33:31.341396+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:33:30.963001+02	t	\N	4	{}	{}	6	t	\N	\N
2	caa3434d-c318-464e-996c-0dca4526c4cb	2026-09-09 10:33:31.539004+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	caa3434d-c318-464e-996c-0dca4526c4cb	2026-09-09 10:33:31.748636+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	1	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	1	fs	1.2.0
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	std	7.0.0
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	2	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	2	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	3	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	3	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	4	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	4	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	5	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	5	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	6	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	6	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	7	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	7	std	8.7.4
48a137cb-bcd1-4a08-8daa-39da44bd3669	8	fs	1.2.0
48a137cb-bcd1-4a08-8daa-39da44bd3669	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	discovery::Discovered[myagent,name=discovered]	{}	2026-09-09 10:33:31.772713+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
48a137cb-bcd1-4a08-8daa-39da44bd3669	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-09-09 10:33:31.772749+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
35d30452-2591-4be0-a6b3-a2b3d7216b97	caa3434d-c318-464e-996c-0dca4526c4cb	1	2026-09-09 10:33:31.497049+02	6	0	{"1abb1cf3-f4a4-5e81-8451-292fd68f0f8b": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "9611554a-a193-5479-b261-b804c355e927": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "9acf62d2-a382-5f21-a016-1f9289fe9bcc": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "a63ac836-250a-5778-996f-fcc40e09df8d": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "a85f8477-34e5-55a7-b7d8-cc6c73af1ab4": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "b973a30d-3abe-5b1c-bc4d-37c21cd741b8": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
08bdb3be-1cd1-4c2a-8223-6841bf57a9d1	dev-4	126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
48a137cb-bcd1-4a08-8daa-39da44bd3669	dev-1	126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	dev-1-twin	126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
48e192b4-5601-455b-b6af-77f12abbff12	dev-2	126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
caa3434d-c318-464e-996c-0dca4526c4cb	dev-3	126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
\.


--
-- Data for Name: environmentmetricsgauge; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricsgauge (environment, metric_name, "timestamp", count, category) FROM stdin;
\.


--
-- Data for Name: environmentmetricstimer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environmentmetricstimer (environment, metric_name, "timestamp", count, value, category) FROM stdin;
\.


--
-- Data for Name: file; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.file (content_hash, content) FROM stdin;
7110eda4d09e062aa5e4a390b0a572ac0d2c0220	\\x31323334
a94a8fe5ccb19ba61c4c0873d391e987982fbbd3	\\x74657374
\.


--
-- Data for Name: inmanta_module; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inmanta_module (name, version, environment, requirements, editable_install) FROM stdin;
std	8.7.4	48a137cb-bcd1-4a08-8daa-39da44bd3669	\N	f
fs	1.2.0	48a137cb-bcd1-4a08-8daa-39da44bd3669	\N	f
std	7.0.0	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	\N	f
fs	1.2.0	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	\N	f
\.


--
-- Data for Name: inmanta_user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inmanta_user (id, username, password_hash, auth_method, is_admin) FROM stdin;
\.


--
-- Data for Name: module_files; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.module_files (inmanta_module_name, inmanta_module_version, environment, file_content_hash, python_module_name, is_byte_code) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification (id, environment, created, title, message, severity, uri, read, cleared, compile_id) FROM stdin;
571deb2d-bfb8-4d0c-a94e-e9d6e529b341	08bdb3be-1cd1-4c2a-8223-6841bf57a9d1	2026-09-09 10:33:31.914837+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/86914943-f19b-42bb-a4ba-0edeac4fc228	f	f	86914943-f19b-42bb-a4ba-0edeac4fc228
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
a12b991a-63b2-46f2-8f2d-89ace82a0467	fact1	value1	48a137cb-bcd1-4a08-8daa-39da44bd3669	std::testing::NullResource[localhost,name=test1]	fact	2026-09-09 10:33:16.091378+02	{}	f
aa254de3-c58b-4473-8fd2-b8df527307e7	fact2	value2	48a137cb-bcd1-4a08-8daa-39da44bd3669	std::testing::NullResource[localhost,name=test2]	fact	2026-09-09 10:33:16.109024+02	{}	t
fd7d5a5c-1bea-45f2-9faf-0fb8d67f0ae0	fact3	value3	48a137cb-bcd1-4a08-8daa-39da44bd3669	std::testing::NullResource[localhost,name=test3]	fact	2026-09-09 10:33:16.116495+02	{}	t
8b6337d0-dada-4f0b-9b11-f1a62dca3ec4	parameter1	value1	48a137cb-bcd1-4a08-8daa-39da44bd3669		fact	2026-09-09 10:33:16.1187+02	{}	f
fe7a52f5-da53-469c-bb63-f1d673166fe3	parameter2	value2	48a137cb-bcd1-4a08-8daa-39da44bd3669		fact	2026-09-09 10:33:16.120906+02	{}	f
0a918264-c389-4412-895b-7975a4cefdd1	parameter3	value3	48a137cb-bcd1-4a08-8daa-39da44bd3669		fact	2026-09-09 10:33:16.123053+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
126d0ec0-8c7c-4954-b7e8-6a5e079b2e4f	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
52142d97-45eb-4b9c-8482-80a3254eb3fd	2026-09-09 10:32:41.098009+02	2026-09-09 10:32:41.103512+02		Init		Using extra environment variables during compile \n	0	51b8b896-617a-4907-841e-d973293be5b3
5088808f-e8b3-4773-b75a-54ec55c572f4	2026-09-09 10:32:41.103804+02	2026-09-09 10:32:41.112294+02		Venv check		Creating new venv at /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env-py3.13\n	0	51b8b896-617a-4907-841e-d973293be5b3
4ae45841-b913-460d-813d-49aaa33129a5	2026-09-09 10:32:41.113896+02	2026-09-09 10:32:41.445217+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	51b8b896-617a-4907-841e-d973293be5b3
a2a3ebb0-8ac2-4d00-88bc-7f4ed70580b5	2026-09-09 10:32:57.150386+02	2026-09-09 10:32:57.499985+02	/tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	47f7bf65-e2d2-490a-a936-17ede5ee887e
b308a5a7-7c4a-4651-be14-6982a555ed5c	2026-09-09 10:32:41.446003+02	2026-09-09 10:32:56.011288+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp_fvsr6qm:\n                                 Pip command: /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp_fvsr6qm inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Downloading python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	51b8b896-617a-4907-841e-d973293be5b3
5e7ebc6c-dfa6-4eea-8b55-1aadb2dc4187	2026-09-09 10:32:57.108874+02	2026-09-09 10:32:57.116708+02		Init		Using extra environment variables during compile \n	0	47f7bf65-e2d2-490a-a936-17ede5ee887e
c4ed1d52-75bd-404e-9526-9e31f54e2dbe	2026-09-09 10:32:57.117709+02	2026-09-09 10:32:57.145287+02		Venv check		Creating new venv at /tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env-py3.13\n	0	47f7bf65-e2d2-490a-a936-17ede5ee887e
2aaca49b-ad2a-4b0f-8dbf-5835eb9ebfb1	2026-09-09 10:32:56.012299+02	2026-09-09 10:32:56.939322+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpnv5nt_2z --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.020 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.074 seconds\n	0	51b8b896-617a-4907-841e-d973293be5b3
b759fc95-1692-4b56-b23b-c9f9a96c3a72	2026-09-09 10:33:12.714485+02	2026-09-09 10:33:12.722324+02		Init		Using extra environment variables during compile \n	0	f1d14a05-c6b6-4dea-8cbf-aef2171279bc
523001a3-a31c-4f98-8b8d-214102f6c688	2026-09-09 10:33:12.723376+02	2026-09-09 10:33:12.725607+02		Venv check		Found existing venv\n	0	f1d14a05-c6b6-4dea-8cbf-aef2171279bc
3f830223-df1a-473c-9439-b1731889a6d7	2026-09-09 10:32:57.500662+02	2026-09-09 10:33:11.568119+02	/tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmppm347idi:\n                                 Pip command: /tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmppm347idi inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	47f7bf65-e2d2-490a-a936-17ede5ee887e
cb026523-6423-4a07-8737-b7395ab931f2	2026-09-09 10:33:11.569089+02	2026-09-09 10:33:12.494007+02	/tmp/tmp1j7qsjv_/server/16c22fa4-02d4-4de6-99f9-c4275fbcf00b/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 16c22fa4-02d4-4de6-99f9-c4275fbcf00b --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp2f0_6_zq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	47f7bf65-e2d2-490a-a936-17ede5ee887e
b4559b5d-6f4e-462e-abb3-80f00d460f15	2026-09-09 10:33:31.909073+02	2026-09-09 10:33:31.913292+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp1j7qsjv_/server/08bdb3be-1cd1-4c2a-8223-6841bf57a9d1/compiler and no repository set.\n	1	86914943-f19b-42bb-a4ba-0edeac4fc228
d12b35bf-f9dc-4e0d-86f7-54f54dd2e0c6	2026-09-09 10:33:12.726617+02	2026-09-09 10:33:13.687348+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpjacd_2qb --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	f1d14a05-c6b6-4dea-8cbf-aef2171279bc
697b7ca6-e880-48fd-a09a-0ac8602596eb	2026-09-09 10:33:13.820174+02	2026-09-09 10:33:13.824591+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	7c8e9c9c-3665-44a0-91f3-405914f8a4fa
15de4ce2-1458-4bdd-a078-742ac7b4bc62	2026-09-09 10:33:13.824802+02	2026-09-09 10:33:13.825196+02		Venv check		Found existing venv\n	0	7c8e9c9c-3665-44a0-91f3-405914f8a4fa
6245bdbf-bb21-43a6-86d4-de196b4a6016	2026-09-09 10:33:13.825357+02	2026-09-09 10:33:14.792192+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmp6xpwfs8w --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.058 seconds\n	0	7c8e9c9c-3665-44a0-91f3-405914f8a4fa
30cdf37c-ddab-4192-b32b-5c3e4a5738a3	2026-09-09 10:33:15.071182+02	2026-09-09 10:33:15.073029+02		Init		Using extra environment variables during compile \n	0	db2cd735-7ca6-414b-9e99-5f43838d6637
ac9759f8-0178-4d14-954b-629605160017	2026-09-09 10:33:15.073275+02	2026-09-09 10:33:15.073691+02		Venv check		Found existing venv\n	0	db2cd735-7ca6-414b-9e99-5f43838d6637
cf350b5f-b81c-4d3b-b10c-8222f4e93019	2026-09-09 10:33:15.073871+02	2026-09-09 10:33:15.97287+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpg7c1_ihi --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	db2cd735-7ca6-414b-9e99-5f43838d6637
cccee844-afa9-4d2b-9dbf-817bf0d0574d	2026-09-09 10:33:16.128859+02	2026-09-09 10:33:16.130818+02		Init		Using extra environment variables during compile \n	0	2a4034a2-2f6f-4b88-9909-032df1633041
f1b0abf1-c405-4ee6-b0e0-35ffd35d0364	2026-09-09 10:33:16.131021+02	2026-09-09 10:33:16.13143+02		Venv check		Found existing venv\n	0	2a4034a2-2f6f-4b88-9909-032df1633041
87f7b0e6-0b37-48ef-bd89-c8624d50f50d	2026-09-09 10:33:17.264484+02	2026-09-09 10:33:17.607676+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6ba5b2d4-846d-4547-8eaf-c0416ce58252
579256bb-03a8-4c37-bf2a-969ebfc70daa	2026-09-09 10:33:16.131586+02	2026-09-09 10:33:17.089566+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcxs8ydho --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.010 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.060 seconds\n	0	2a4034a2-2f6f-4b88-9909-032df1633041
90af99c3-77bf-403e-bf13-0af913511e60	2026-09-09 10:33:17.257594+02	2026-09-09 10:33:17.262537+02		Init		Using extra environment variables during compile \n	0	6ba5b2d4-846d-4547-8eaf-c0416ce58252
83c3d7b0-18f9-416e-b004-9161b10f98d6	2026-09-09 10:33:17.262784+02	2026-09-09 10:33:17.263228+02		Venv check		Found existing venv\n	0	6ba5b2d4-846d-4547-8eaf-c0416ce58252
fb2733c0-d620-4e2a-ac90-e67923a0458d	2026-09-09 10:33:17.608277+02	2026-09-09 10:33:30.023458+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpqrf6yyqz:\n                                 Pip command: /tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpqrf6yyqz inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.13/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.13/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.13/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	6ba5b2d4-846d-4547-8eaf-c0416ce58252
4b24a817-e879-4a8d-a440-f1dfcadf12f6	2026-09-09 10:33:30.024411+02	2026-09-09 10:33:30.924011+02	/tmp/tmp1j7qsjv_/server/48a137cb-bcd1-4a08-8daa-39da44bd3669/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 48a137cb-bcd1-4a08-8daa-39da44bd3669 --server_address localhost --server_port 38269 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp4eyg2wfm --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38269/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38269/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.052 seconds\n	0	6ba5b2d4-846d-4547-8eaf-c0416ce58252
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	11c199c4-4629-4a6c-ab13-fc1554a33416
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	11c199c4-4629-4a6c-ab13-fc1554a33416
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	b665add0-cf3c-4083-b08c-660ec377b18a
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b665add0-cf3c-4083-b08c-660ec377b18a
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	c46fac04-4980-4bf5-8c21-de25f536a252
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	c46fac04-4980-4bf5-8c21-de25f536a252
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	559a6f8b-0024-4d65-85e9-ca16a961ad33
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	559a6f8b-0024-4d65-85e9-ca16a961ad33
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	559a6f8b-0024-4d65-85e9-ca16a961ad33
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	52f1648b-8848-415c-9c45-2201dadb97c9
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	52f1648b-8848-415c-9c45-2201dadb97c9
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	5e9cad68-d216-4bdb-9279-9e2fc5673cfe
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	5e9cad68-d216-4bdb-9279-9e2fc5673cfe
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	8aeb8bc7-8a2a-4df3-8837-5c13d512e0d4
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	8aeb8bc7-8a2a-4df3-8837-5c13d512e0d4
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	99bf0c9d-74e8-427f-b814-251bc9757ff1
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	99bf0c9d-74e8-427f-b814-251bc9757ff1
48a137cb-bcd1-4a08-8daa-39da44bd3669	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	dfbcc89a-61ff-4736-8e39-2728d1063d77
48a137cb-bcd1-4a08-8daa-39da44bd3669	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	eb01e067-5211-460d-a5cb-f4928d51e46e
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	ae95faa2-5fa3-4360-a171-ab6f8bf288bb
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ae95faa2-5fa3-4360-a171-ab6f8bf288bb
48a137cb-bcd1-4a08-8daa-39da44bd3669	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	b145f604-7491-443b-add0-22a64ffbb061
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	d06aaf95-5694-411e-9e88-12c858f99525
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	d06aaf95-5694-411e-9e88-12c858f99525
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
3da9b23e-b332-45ae-a057-af373f319563	caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-09-09 10:33:31.600557+02
41c970d9-76cf-4e69-a6f9-8d85758864c0	caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-09-09 10:33:31.622106+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key11]	2026-09-09 10:33:31.600557+02	\N	2026-09-09 10:33:31.600557+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.56412+02	f	3da9b23e-b332-45ae-a057-af373f319563	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	std::AgentConfig[internal,agentname=localhost]	2026-09-09 10:32:56.970124+02	\N	2026-09-09 10:32:56.970124+02	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:32:56.954138+02	f	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key10]	2026-09-09 10:33:31.622106+02	\N	2026-09-09 10:33:31.622106+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.56412+02	f	41c970d9-76cf-4e69-a6f9-8d85758864c0	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test]	2026-09-09 10:32:56.974929+02	\N	2026-09-09 10:32:56.974929+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:32:56.954138+02	f	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-09-09 10:33:31.358317+02	\N	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key9]	2026-09-09 10:33:31.626317+02	2026-09-09 10:33:31.623177+02	2026-09-09 10:33:31.626317+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.56412+02	t	\N	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	std::AgentConfig[internal,agentname=localhost]	2026-09-09 10:33:12.59319+02	\N	2026-09-09 10:33:12.59319+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:12.545413+02	f	\N	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	fs::File[localhost,path=/tmp/test]	2026-09-09 10:33:12.613514+02	\N	2026-09-09 10:33:12.613514+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:12.545413+02	f	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key1]	2026-09-09 10:33:31.37506+02	2026-09-09 10:33:31.371631+02	2026-09-09 10:33:31.37506+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.358317+02	t	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key7]	2026-09-09 10:33:31.630008+02	2026-09-09 10:33:31.627045+02	2026-09-09 10:33:31.630008+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.56412+02	t	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Fail[agent1,key=key2]	2026-09-09 10:33:31.377761+02	\N	2026-09-09 10:33:31.377761+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:31.358317+02	f	\N	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	fs::File[localhost,path=/tmp/test_orphan]	2026-09-09 10:33:14.944312+02	\N	2026-09-09 10:33:14.944312+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:14.918136+02	f	\N	3
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key3]	2026-09-09 10:33:31.3794+02	\N	2026-09-09 10:33:31.3794+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-09-09 10:33:31.358317+02	f	\N	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	test::Resource[agent2,key=key2]	2026-09-09 10:33:30.996625+02	\N	2026-09-09 10:33:30.996625+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:30.988002+02	f	\N	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	test::Resource[agent3,key=key3]	2026-09-09 10:33:30.994678+02	\N	2026-09-09 10:33:30.994678+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-09-09 10:33:30.988002+02	f	\N	7
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-09-09 10:33:31.358317+02	\N	\N	\N
caa3434d-c318-464e-996c-0dca4526c4cb	test::Resource[agent1,key=key6]	2026-09-09 10:33:31.370598+02	2026-09-09 10:33:31.364939+02	2026-09-09 10:33:31.370598+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-09 10:33:31.358317+02	t	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	11c199c4-4629-4a6c-ab13-fc1554a33416	\N
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	b665add0-cf3c-4083-b08c-660ec377b18a	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	c46fac04-4980-4bf5-8c21-de25f536a252	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	559a6f8b-0024-4d65-85e9-ca16a961ad33	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	52f1648b-8848-415c-9c45-2201dadb97c9	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	5e9cad68-d216-4bdb-9279-9e2fc5673cfe	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	8aeb8bc7-8a2a-4df3-8837-5c13d512e0d4	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	99bf0c9d-74e8-427f-b814-251bc9757ff1	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	dfbcc89a-61ff-4736-8e39-2728d1063d77	set-a
48a137cb-bcd1-4a08-8daa-39da44bd3669	eb01e067-5211-460d-a5cb-f4928d51e46e	set-b
48a137cb-bcd1-4a08-8daa-39da44bd3669	ae95faa2-5fa3-4360-a171-ab6f8bf288bb	\N
48a137cb-bcd1-4a08-8daa-39da44bd3669	b145f604-7491-443b-add0-22a64ffbb061	set-a
caa3434d-c318-464e-996c-0dca4526c4cb	47f1a077-0f8b-4479-bea6-ec1ea54eeddd	\N
caa3434d-c318-464e-996c-0dca4526c4cb	c00802a0-1d52-4254-80a3-a2908e4ee649	\N
caa3434d-c318-464e-996c-0dca4526c4cb	d06aaf95-5694-411e-9e88-12c858f99525	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	1	11c199c4-4629-4a6c-ab13-fc1554a33416
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	b665add0-cf3c-4083-b08c-660ec377b18a
48a137cb-bcd1-4a08-8daa-39da44bd3669	2	c46fac04-4980-4bf5-8c21-de25f536a252
48a137cb-bcd1-4a08-8daa-39da44bd3669	3	559a6f8b-0024-4d65-85e9-ca16a961ad33
48a137cb-bcd1-4a08-8daa-39da44bd3669	4	52f1648b-8848-415c-9c45-2201dadb97c9
48a137cb-bcd1-4a08-8daa-39da44bd3669	5	5e9cad68-d216-4bdb-9279-9e2fc5673cfe
48a137cb-bcd1-4a08-8daa-39da44bd3669	6	8aeb8bc7-8a2a-4df3-8837-5c13d512e0d4
48a137cb-bcd1-4a08-8daa-39da44bd3669	7	99bf0c9d-74e8-427f-b814-251bc9757ff1
48a137cb-bcd1-4a08-8daa-39da44bd3669	7	dfbcc89a-61ff-4736-8e39-2728d1063d77
48a137cb-bcd1-4a08-8daa-39da44bd3669	7	eb01e067-5211-460d-a5cb-f4928d51e46e
48a137cb-bcd1-4a08-8daa-39da44bd3669	8	ae95faa2-5fa3-4360-a171-ab6f8bf288bb
48a137cb-bcd1-4a08-8daa-39da44bd3669	8	b145f604-7491-443b-add0-22a64ffbb061
caa3434d-c318-464e-996c-0dca4526c4cb	1	47f1a077-0f8b-4479-bea6-ec1ea54eeddd
caa3434d-c318-464e-996c-0dca4526c4cb	2	c00802a0-1d52-4254-80a3-a2908e4ee649
caa3434d-c318-464e-996c-0dca4526c4cb	3	d06aaf95-5694-411e-9e88-12c858f99525
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
43037a3c-b6cf-44d9-9ec1-99cb8436bf14	store	2026-09-09 10:32:56.92082+02	2026-09-09 10:32:56.927968+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-09T10:32:56.927978+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
f66d289b-ea67-471b-8afb-bd80cf1a9887	deploy	2026-09-09 10:32:56.961414+02	2026-09-09 10:32:56.970124+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:32:56.969317+02:00\\"}"}	unavailable	\N	nochange	48a137cb-bcd1-4a08-8daa-39da44bd3669	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5a850b81-6fda-4ed9-b334-4da9b60e0ff5	deploy	2026-09-09 10:32:56.973786+02	2026-09-09 10:32:56.974929+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:32:56.974508+02:00\\"}"}	unavailable	\N	nochange	48a137cb-bcd1-4a08-8daa-39da44bd3669	1	{"fs::File[localhost,path=/tmp/test],v=1"}
ae6bc28e-7ad5-4caa-98c8-9cdea2a57c92	store	2026-09-09 10:33:12.481487+02	2026-09-09 10:33:12.487358+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-09T10:33:12.487367+02:00\\"}"}	\N	\N	\N	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
a2314d8c-fa17-4735-b5c2-642313ae2e7a	deploy	2026-09-09 10:33:12.565078+02	2026-09-09 10:33:12.59319+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:12.591624+02:00\\"}"}	unavailable	\N	nochange	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
15e918b9-af81-456f-86ac-9e40fa0340e6	deploy	2026-09-09 10:33:12.610752+02	2026-09-09 10:33:12.613514+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:12.612997+02:00\\"}"}	unavailable	\N	nochange	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1	{"fs::File[localhost,path=/tmp/test],v=1"}
0ecd7550-78ad-4ab2-9173-fbb79267c277	store	2026-09-09 10:33:13.679514+02	2026-09-09 10:33:13.681753+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-09T10:33:13.681761+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	2	{"fs::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
fc747222-3dfc-4253-bee6-dcbc685a96e0	store	2026-09-09 10:33:14.78123+02	2026-09-09 10:33:14.78637+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-09T10:33:14.786377+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	3	{"fs::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
6cb84d88-5f23-4231-98ca-4b77d7fa6d91	deploy	2026-09-09 10:33:14.936556+02	2026-09-09 10:33:14.944312+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-09-09T10:33:14.942904+02:00\\"}"}	unavailable	\N	nochange	48a137cb-bcd1-4a08-8daa-39da44bd3669	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
3fae8ac0-ad3e-4f2a-96b4-c11f482b41ed	store	2026-09-09 10:33:15.965128+02	2026-09-09 10:33:15.967339+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-09-09T10:33:15.967347+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	4	{"fs::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
171ffa68-5996-429f-8485-2a56891f52cf	store	2026-09-09 10:33:17.080324+02	2026-09-09 10:33:17.082601+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-09-09T10:33:17.082610+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
f1aa4e83-1779-4128-b510-931621fb1e5a	store	2026-09-09 10:33:30.914349+02	2026-09-09 10:33:30.916784+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-09-09T10:33:30.916795+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	6	{"fs::File[localhost,path=/tmp/test],v=6","std::AgentConfig[internal,agentname=localhost],v=6"}
126f62e0-600d-43bb-a388-e54d2dd3531d	store	2026-09-09 10:33:30.962897+02	2026-09-09 10:33:30.967064+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-09-09T10:33:30.967072+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	7	{"test::Resource[agent3,key=key3],v=7","std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7"}
e9c2d3b4-a618-476f-9bfb-38d96486631f	deploy	2026-09-09 10:33:30.992922+02	2026-09-09 10:33:30.994678+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-09-09T10:33:30.994037+02:00\\"}"}	unavailable	\N	nochange	48a137cb-bcd1-4a08-8daa-39da44bd3669	7	{"test::Resource[agent3,key=key3],v=7"}
cf897cdc-54b4-4ca8-b614-d1244a2ac9a3	deploy	2026-09-09 10:33:30.994738+02	2026-09-09 10:33:30.996625+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-09-09T10:33:30.996125+02:00\\"}"}	unavailable	\N	nochange	48a137cb-bcd1-4a08-8daa-39da44bd3669	7	{"test::Resource[agent2,key=key2],v=7"}
c601392e-89e3-480b-a977-48c525def476	store	2026-09-09 10:33:31.134594+02	2026-09-09 10:33:31.157335+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-09-09T10:33:31.157351+02:00\\"}"}	\N	\N	\N	48a137cb-bcd1-4a08-8daa-39da44bd3669	8	{"std::AgentConfig[internal,agentname=localhost],v=8","fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
63c3676f-d6ed-46b0-a4a9-396de3839586	store	2026-09-09 10:33:31.341094+02	2026-09-09 10:33:31.349598+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-09T10:33:31.349626+02:00\\"}"}	\N	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key1],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key5],v=1"}
97343aa3-70d2-4a52-8cbb-19ce153f62de	deploy	2026-09-09 10:33:31.364994+02	2026-09-09 10:33:31.370598+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 6c502ed5-5956-4ed2-9f21-c12794dd40d3).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"6c502ed5-5956-4ed2-9f21-c12794dd40d3\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.366276+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 6c502ed5-5956-4ed2-9f21-c12794dd40d3) - duration: 0.0042 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0042192935943603516, \\"deploy_id\\": \\"6c502ed5-5956-4ed2-9f21-c12794dd40d3\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.370558+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key6],v=1"}
3f08f2f7-0e16-4c31-9250-15eccb1a0264	dryrun	2026-09-09 10:33:31.525812+02	2026-09-09 10:33:31.526857+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.525972+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006990432739257812, \\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.526809+02:00\\"}"}	dry	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key1],v=1"}
ecc56381-308e-4e7a-92c2-9697608eb4fd	dryrun	2026-09-09 10:33:31.542344+02	2026-09-09 10:33:31.543661+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.542545+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97 - duration 0.0009 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.000896453857421875, \\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.543602+02:00\\"}"}	dry	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key3],v=1"}
eab5f278-d523-47ad-b453-cd8aa67079ca	dryrun	2026-09-09 10:33:31.566854+02	2026-09-09 10:33:31.567887+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.567013+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006799697875976562, \\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.567832+02:00\\"}"}	dry	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key6],v=1"}
b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	store	2026-09-09 10:33:31.74832+02	2026-09-09 10:33:31.756751+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-09T10:33:31.756776+02:00\\"}"}	\N	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	3	{"test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key8],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key5],v=3"}
8f5e59b3-d604-44a2-bd6e-8e25717e8e0f	deploy	2026-09-09 10:33:31.371664+02	2026-09-09 10:33:31.37506+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 7d7dddee-db79-459c-92d6-65994fd183b6).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"7d7dddee-db79-459c-92d6-65994fd183b6\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.372365+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 7d7dddee-db79-459c-92d6-65994fd183b6) - duration: 0.0026 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0026121139526367188, \\"deploy_id\\": \\"7d7dddee-db79-459c-92d6-65994fd183b6\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.375022+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key1],v=1"}
1502d7b3-f7dd-45ae-9b81-ed4c84b5ee6f	deploy	2026-09-09 10:33:31.375969+02	2026-09-09 10:33:31.377761+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 7614b990-0d1c-47c0-a7f7-1e73c4950e24).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"7614b990-0d1c-47c0-a7f7-1e73c4950e24\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.376597+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2653, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.377234+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 7614b990-0d1c-47c0-a7f7-1e73c4950e24) - duration: 0.0011 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0011026859283447266, \\"deploy_id\\": \\"7614b990-0d1c-47c0-a7f7-1e73c4950e24\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.377736+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Fail[agent1,key=key2],v=1"}
e8bb6436-4b71-4f96-b59c-effd376a4414	deploy	2026-09-09 10:33:31.378603+02	2026-09-09 10:33:31.3794+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d502e180-4120-4549-8cc3-ba166821d98a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"d502e180-4120-4549-8cc3-ba166821d98a\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.379158+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.379303+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: d502e180-4120-4549-8cc3-ba166821d98a) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00019049644470214844, \\"deploy_id\\": \\"d502e180-4120-4549-8cc3-ba166821d98a\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.379380+02:00\\"}"}	skipped	\N	nochange	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key3],v=1"}
924fde6f-6bf6-4cf8-8441-6003e3084a20	dryrun	2026-09-09 10:33:31.50638+02	2026-09-09 10:33:31.507641+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.506566+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97 - duration 0.0009 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00086212158203125, \\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.507584+02:00\\"}"}	dry	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Fail[agent1,key=key2],v=1"}
2b162102-75d4-4327-8b72-e4af61126bc6	store	2026-09-09 10:33:31.538058+02	2026-09-09 10:33:31.549413+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-09T10:33:31.549438+02:00\\"}"}	\N	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	2	{"test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key3],v=2"}
7653a8b7-9374-49e0-a91c-ee5bcb786df3	dryrun	2026-09-09 10:33:31.553157+02	2026-09-09 10:33:31.554447+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.553397+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 35d30452-2591-4be0-a6b3-a2b3d7216b97 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007479190826416016, \\"dry_run_id\\": \\"35d30452-2591-4be0-a6b3-a2b3d7216b97\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.554370+02:00\\"}"}	dry	\N	\N	caa3434d-c318-464e-996c-0dca4526c4cb	1	{"test::Resource[agent1,key=key5],v=1"}
fe6cbed8-c109-42cc-bea3-e5df215d035a	deploy	2026-09-09 10:33:31.586615+02	2026-09-09 10:33:31.600557+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 5b53547e-69a3-4a7b-ad85-6dee1019e8bd).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"5b53547e-69a3-4a7b-ad85-6dee1019e8bd\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.591257+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.591764+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 5b53547e-69a3-4a7b-ad85-6dee1019e8bd) - duration: 0.0090 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.009043693542480469, \\"deploy_id\\": \\"5b53547e-69a3-4a7b-ad85-6dee1019e8bd\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.600449+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	caa3434d-c318-464e-996c-0dca4526c4cb	2	{"test::Resource[agent1,key=key11],v=2"}
c9c332f5-943f-4c8c-9a85-f84e33e3d06b	deploy	2026-09-09 10:33:31.606951+02	2026-09-09 10:33:31.622106+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: bc16af1a-d063-422f-9b20-366e1f6d666f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"bc16af1a-d063-422f-9b20-366e1f6d666f\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.610549+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.611158+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: bc16af1a-d063-422f-9b20-366e1f6d666f) - duration: 0.0114 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.011437654495239258, \\"deploy_id\\": \\"bc16af1a-d063-422f-9b20-366e1f6d666f\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.622069+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	caa3434d-c318-464e-996c-0dca4526c4cb	2	{"test::Resource[agent1,key=key10],v=2"}
efcd4251-3511-4275-aad9-5a792506fe5b	deploy	2026-09-09 10:33:31.623208+02	2026-09-09 10:33:31.626317+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: e63353fb-5540-42af-abbb-4344eef65648).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"e63353fb-5540-42af-abbb-4344eef65648\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.623789+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: e63353fb-5540-42af-abbb-4344eef65648) - duration: 0.0025 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.002458810806274414, \\"deploy_id\\": \\"e63353fb-5540-42af-abbb-4344eef65648\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.626288+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	caa3434d-c318-464e-996c-0dca4526c4cb	2	{"test::Resource[agent1,key=key9],v=2"}
72845136-fb97-4085-8669-3e660143baf6	deploy	2026-09-09 10:33:31.627074+02	2026-09-09 10:33:31.630008+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 5038105f-961d-42eb-8fc1-765eeddcc44c).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"5038105f-961d-42eb-8fc1-765eeddcc44c\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.627625+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 5038105f-961d-42eb-8fc1-765eeddcc44c) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0023169517517089844, \\"deploy_id\\": \\"5038105f-961d-42eb-8fc1-765eeddcc44c\\"}, \\"timestamp\\": \\"2026-09-09T10:33:31.629981+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	caa3434d-c318-464e-996c-0dca4526c4cb	2	{"test::Resource[agent1,key=key7],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
48a137cb-bcd1-4a08-8daa-39da44bd3669	43037a3c-b6cf-44d9-9ec1-99cb8436bf14	fs::File[localhost,path=/tmp/test]	1
48a137cb-bcd1-4a08-8daa-39da44bd3669	43037a3c-b6cf-44d9-9ec1-99cb8436bf14	std::AgentConfig[internal,agentname=localhost]	1
48a137cb-bcd1-4a08-8daa-39da44bd3669	f66d289b-ea67-471b-8afb-bd80cf1a9887	std::AgentConfig[internal,agentname=localhost]	1
48a137cb-bcd1-4a08-8daa-39da44bd3669	5a850b81-6fda-4ed9-b334-4da9b60e0ff5	fs::File[localhost,path=/tmp/test]	1
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	ae6bc28e-7ad5-4caa-98c8-9cdea2a57c92	fs::File[localhost,path=/tmp/test]	1
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	ae6bc28e-7ad5-4caa-98c8-9cdea2a57c92	std::AgentConfig[internal,agentname=localhost]	1
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	a2314d8c-fa17-4735-b5c2-642313ae2e7a	std::AgentConfig[internal,agentname=localhost]	1
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	15e918b9-af81-456f-86ac-9e40fa0340e6	fs::File[localhost,path=/tmp/test]	1
48a137cb-bcd1-4a08-8daa-39da44bd3669	0ecd7550-78ad-4ab2-9173-fbb79267c277	fs::File[localhost,path=/tmp/test]	2
48a137cb-bcd1-4a08-8daa-39da44bd3669	0ecd7550-78ad-4ab2-9173-fbb79267c277	std::AgentConfig[internal,agentname=localhost]	2
48a137cb-bcd1-4a08-8daa-39da44bd3669	fc747222-3dfc-4253-bee6-dcbc685a96e0	fs::File[localhost,path=/tmp/test]	3
48a137cb-bcd1-4a08-8daa-39da44bd3669	fc747222-3dfc-4253-bee6-dcbc685a96e0	std::AgentConfig[internal,agentname=localhost]	3
48a137cb-bcd1-4a08-8daa-39da44bd3669	fc747222-3dfc-4253-bee6-dcbc685a96e0	fs::File[localhost,path=/tmp/test_orphan]	3
48a137cb-bcd1-4a08-8daa-39da44bd3669	6cb84d88-5f23-4231-98ca-4b77d7fa6d91	fs::File[localhost,path=/tmp/test_orphan]	3
48a137cb-bcd1-4a08-8daa-39da44bd3669	3fae8ac0-ad3e-4f2a-96b4-c11f482b41ed	fs::File[localhost,path=/tmp/test]	4
48a137cb-bcd1-4a08-8daa-39da44bd3669	3fae8ac0-ad3e-4f2a-96b4-c11f482b41ed	std::AgentConfig[internal,agentname=localhost]	4
48a137cb-bcd1-4a08-8daa-39da44bd3669	171ffa68-5996-429f-8485-2a56891f52cf	std::AgentConfig[internal,agentname=localhost]	5
48a137cb-bcd1-4a08-8daa-39da44bd3669	171ffa68-5996-429f-8485-2a56891f52cf	fs::File[localhost,path=/tmp/test]	5
48a137cb-bcd1-4a08-8daa-39da44bd3669	f1aa4e83-1779-4128-b510-931621fb1e5a	fs::File[localhost,path=/tmp/test]	6
48a137cb-bcd1-4a08-8daa-39da44bd3669	f1aa4e83-1779-4128-b510-931621fb1e5a	std::AgentConfig[internal,agentname=localhost]	6
48a137cb-bcd1-4a08-8daa-39da44bd3669	126f62e0-600d-43bb-a388-e54d2dd3531d	test::Resource[agent3,key=key3]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	126f62e0-600d-43bb-a388-e54d2dd3531d	std::AgentConfig[internal,agentname=localhost]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	126f62e0-600d-43bb-a388-e54d2dd3531d	fs::File[localhost,path=/tmp/test]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	126f62e0-600d-43bb-a388-e54d2dd3531d	test::Resource[agent2,key=key2]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	e9c2d3b4-a618-476f-9bfb-38d96486631f	test::Resource[agent3,key=key3]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	cf897cdc-54b4-4ca8-b614-d1244a2ac9a3	test::Resource[agent2,key=key2]	7
48a137cb-bcd1-4a08-8daa-39da44bd3669	c601392e-89e3-480b-a977-48c525def476	std::AgentConfig[internal,agentname=localhost]	8
48a137cb-bcd1-4a08-8daa-39da44bd3669	c601392e-89e3-480b-a977-48c525def476	fs::File[localhost,path=/tmp/test]	8
48a137cb-bcd1-4a08-8daa-39da44bd3669	c601392e-89e3-480b-a977-48c525def476	test::Resource[agent2,key=key2]	8
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Resource[agent1,key=key3]	1
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Resource[agent1,key=key4]	1
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Resource[agent1,key=key6]	1
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Resource[agent1,key=key1]	1
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Fail[agent1,key=key2]	1
caa3434d-c318-464e-996c-0dca4526c4cb	63c3676f-d6ed-46b0-a4a9-396de3839586	test::Resource[agent1,key=key5]	1
caa3434d-c318-464e-996c-0dca4526c4cb	97343aa3-70d2-4a52-8cbb-19ce153f62de	test::Resource[agent1,key=key6]	1
caa3434d-c318-464e-996c-0dca4526c4cb	8f5e59b3-d604-44a2-bd6e-8e25717e8e0f	test::Resource[agent1,key=key1]	1
caa3434d-c318-464e-996c-0dca4526c4cb	1502d7b3-f7dd-45ae-9b81-ed4c84b5ee6f	test::Fail[agent1,key=key2]	1
caa3434d-c318-464e-996c-0dca4526c4cb	e8bb6436-4b71-4f96-b59c-effd376a4414	test::Resource[agent1,key=key3]	1
caa3434d-c318-464e-996c-0dca4526c4cb	924fde6f-6bf6-4cf8-8441-6003e3084a20	test::Fail[agent1,key=key2]	1
caa3434d-c318-464e-996c-0dca4526c4cb	3f08f2f7-0e16-4c31-9250-15eccb1a0264	test::Resource[agent1,key=key1]	1
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key9]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key4]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key7]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key11]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key1]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key10]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key5]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Fail[agent1,key=key2]	2
caa3434d-c318-464e-996c-0dca4526c4cb	2b162102-75d4-4327-8b72-e4af61126bc6	test::Resource[agent1,key=key3]	2
caa3434d-c318-464e-996c-0dca4526c4cb	ecc56381-308e-4e7a-92c2-9697608eb4fd	test::Resource[agent1,key=key3]	1
caa3434d-c318-464e-996c-0dca4526c4cb	7653a8b7-9374-49e0-a91c-ee5bcb786df3	test::Resource[agent1,key=key5]	1
caa3434d-c318-464e-996c-0dca4526c4cb	eab5f278-d523-47ad-b453-cd8aa67079ca	test::Resource[agent1,key=key6]	1
caa3434d-c318-464e-996c-0dca4526c4cb	fe6cbed8-c109-42cc-bea3-e5df215d035a	test::Resource[agent1,key=key11]	2
caa3434d-c318-464e-996c-0dca4526c4cb	c9c332f5-943f-4c8c-9a85-f84e33e3d06b	test::Resource[agent1,key=key10]	2
caa3434d-c318-464e-996c-0dca4526c4cb	efcd4251-3511-4275-aad9-5a792506fe5b	test::Resource[agent1,key=key9]	2
caa3434d-c318-464e-996c-0dca4526c4cb	72845136-fb97-4085-8669-3e660143baf6	test::Resource[agent1,key=key7]	2
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key3]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key1]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key7]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key8]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Fail[agent1,key=key2]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key4]	3
caa3434d-c318-464e-996c-0dca4526c4cb	b30df5ee-bd47-471f-bfc6-e10c2eecc1bd	test::Resource[agent1,key=key5]	3
\.


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role (id, name) FROM stdin;
\.


--
-- Data for Name: role_assignment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role_assignment (user_id, environment, role_id) FROM stdin;
\.


--
-- Data for Name: scheduler; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scheduler (environment, last_processed_model_version) FROM stdin;
16c22fa4-02d4-4de6-99f9-c4275fbcf00b	1
48a137cb-bcd1-4a08-8daa-39da44bd3669	8
caa3434d-c318-464e-996c-0dca4526c4cb	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	48a137cb-bcd1-4a08-8daa-39da44bd3669	2026-09-09 10:32:40.766033+02	\N	95893e39-2fb6-4519-976c-83621f76a240
hugo-Latitude-5421	16c22fa4-02d4-4de6-99f9-c4275fbcf00b	2026-09-09 10:32:40.887441+02	\N	5031403e-55cd-42e0-93f9-6d8e7689f751
hugo-Latitude-5421	caa3434d-c318-464e-996c-0dca4526c4cb	2026-09-09 10:33:31.197134+02	2026-09-09 10:33:31.722726+02	e3d7f5e8-7135-406e-869d-b452b6f787e5
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150}
\.


--
-- Data for Name: token; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.token (jti, created_by, client_types, environment, issued_at, expires_at, last_used, revoked_at) FROM stdin;
\.


--
-- Data for Name: unknownparameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.unknownparameter (id, name, environment, source, resource_id, version, metadata, resolved) FROM stdin;
\.


--
-- Name: agent_modules agent_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_pkey PRIMARY KEY (environment, cm_version, inmanta_module_name, agent_name);


--
-- Name: agent agent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_pkey PRIMARY KEY (environment, name);


--
-- Name: schedulersession agentprocess_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedulersession
    ADD CONSTRAINT agentprocess_pkey PRIMARY KEY (sid);


--
-- Name: compile compile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_pkey PRIMARY KEY (id);


--
-- Name: configurationmodel_modules configurationmodel_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_pkey PRIMARY KEY (environment, cm_version, inmanta_module_name);


--
-- Name: configurationmodel configurationmodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel
    ADD CONSTRAINT configurationmodel_pkey PRIMARY KEY (environment, version);


--
-- Name: discoveredresource discoveredresource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discoveredresource
    ADD CONSTRAINT discoveredresource_pkey PRIMARY KEY (environment, discovered_resource_id);


--
-- Name: dryrun dryrun_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_pkey PRIMARY KEY (id);


--
-- Name: environment environment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_pkey PRIMARY KEY (id);


--
-- Name: environmentmetricsgauge environmentmetricsgauge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricsgauge
    ADD CONSTRAINT environmentmetricsgauge_pkey PRIMARY KEY (environment, "timestamp", metric_name, category);


--
-- Name: environmentmetricstimer environmentmetricstimer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricstimer
    ADD CONSTRAINT environmentmetricstimer_pkey PRIMARY KEY (environment, "timestamp", metric_name, category);


--
-- Name: file file_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file
    ADD CONSTRAINT file_pkey PRIMARY KEY (content_hash);


--
-- Name: inmanta_module inmanta_module_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_module
    ADD CONSTRAINT inmanta_module_pkey PRIMARY KEY (environment, name, version);


--
-- Name: module_files module_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.module_files
    ADD CONSTRAINT module_files_pkey PRIMARY KEY (environment, inmanta_module_name, inmanta_module_version, python_module_name);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (environment, id);


--
-- Name: parameter parameter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parameter
    ADD CONSTRAINT parameter_pkey PRIMARY KEY (id);


--
-- Name: project project_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_name_key UNIQUE (name);


--
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (id);


--
-- Name: report report_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report
    ADD CONSTRAINT report_pkey PRIMARY KEY (id);


--
-- Name: resource_diff resource_diff_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_diff
    ADD CONSTRAINT resource_diff_pkey PRIMARY KEY (id);


--
-- Name: resource_persistent_state resource_persistent_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_persistent_state
    ADD CONSTRAINT resource_persistent_state_pkey PRIMARY KEY (environment, resource_id);


--
-- Name: resource resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, resource_set, resource_id);


--
-- Name: resource_set_configuration_model resource_set_configuration_model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_set_configuration_model
    ADD CONSTRAINT resource_set_configuration_model_pkey PRIMARY KEY (environment, model, resource_set);


--
-- Name: resource_set resource_set_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_set
    ADD CONSTRAINT resource_set_pkey PRIMARY KEY (environment, id);


--
-- Name: resourceaction resourceaction_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_pkey PRIMARY KEY (action_id);


--
-- Name: resourceaction_resource resourceaction_resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_pkey PRIMARY KEY (environment, resource_id, resource_version, resource_action_id);


--
-- Name: role_assignment role_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment
    ADD CONSTRAINT role_assignment_pkey PRIMARY KEY (user_id, environment, role_id);


--
-- Name: role role_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_name_key UNIQUE (name);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- Name: scheduler scheduler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduler
    ADD CONSTRAINT scheduler_pkey PRIMARY KEY (environment);


--
-- Name: schemamanager schemamanager_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schemamanager
    ADD CONSTRAINT schemamanager_pkey PRIMARY KEY (name);


--
-- Name: token token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token
    ADD CONSTRAINT token_pkey PRIMARY KEY (jti);


--
-- Name: unknownparameter unknownparameter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_pkey PRIMARY KEY (id);


--
-- Name: inmanta_user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_user
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: inmanta_user user_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_user
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: agent_modules_environment_agent_name_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_modules_environment_agent_name_index ON public.agent_modules USING btree (environment, agent_name);


--
-- Name: compile_completed_environment_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_completed_environment_idx ON public.compile USING btree (completed, environment);


--
-- Name: compile_env_remote_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_remote_id_index ON public.compile USING btree (environment, remote_id);


--
-- Name: compile_env_requested_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_requested_index ON public.compile USING btree (environment, requested);


--
-- Name: compile_env_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_env_started_index ON public.compile USING btree (environment, started DESC);


--
-- Name: compile_environment_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_environment_version_index ON public.compile USING btree (environment, version);


--
-- Name: compile_substitute_compile_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX compile_substitute_compile_id_index ON public.compile USING btree (substitute_compile_id);


--
-- Name: configurationmodel_env_released_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX configurationmodel_env_released_version_index ON public.configurationmodel USING btree (environment, released, version DESC);


--
-- Name: configurationmodel_env_version_total_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX configurationmodel_env_version_total_index ON public.configurationmodel USING btree (environment, version DESC, total);


--
-- Name: configurationmodel_modules_inmanta_module_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX configurationmodel_modules_inmanta_module_index ON public.configurationmodel_modules USING btree (environment, inmanta_module_name, inmanta_module_version);


--
-- Name: dryrun_env_model_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX dryrun_env_model_index ON public.dryrun USING btree (environment, model);


--
-- Name: environment_name_project_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX environment_name_project_index ON public.environment USING btree (project, name);


--
-- Name: notification_env_created_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX notification_env_created_id_index ON public.notification USING btree (environment, created DESC, id);


--
-- Name: parameter_env_name_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_env_name_resource_id_index ON public.parameter USING btree (environment, name, resource_id);


--
-- Name: parameter_environment_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_environment_resource_id_index ON public.parameter USING btree (environment, resource_id);


--
-- Name: parameter_metadata_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_metadata_index ON public.parameter USING gin (metadata jsonb_path_ops);


--
-- Name: parameter_updated_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX parameter_updated_index ON public.parameter USING btree (updated);


--
-- Name: report_compile_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_compile_index ON public.report USING btree (compile);


--
-- Name: report_started_compile_returncode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX report_started_compile_returncode ON public.report USING btree (compile, returncode);


--
-- Name: resource_attributes_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_attributes_index ON public.resource USING gin (attributes jsonb_path_ops);


--
-- Name: resource_diff_environment_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_diff_environment_created ON public.resource_diff USING btree (environment, created);


--
-- Name: resource_diff_environment_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_diff_environment_resource_id ON public.resource_diff USING btree (environment, resource_id);


--
-- Name: resource_env_attr_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_attr_hash_index ON public.resource USING btree (environment, attribute_hash);


--
-- Name: resource_environment_agent_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_agent_idx ON public.resource USING btree (environment, agent);


--
-- Name: resource_environment_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_id_index ON public.resource USING btree (environment, resource_id);


--
-- Name: resource_environment_resource_id_value_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_id_value_index ON public.resource USING btree (environment, resource_id_value);


--
-- Name: resource_environment_resource_set_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_set_id_index ON public.resource USING btree (environment, resource_set);


--
-- Name: resource_environment_resource_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_type_index ON public.resource USING btree (environment, resource_type);


--
-- Name: resource_persistent_state_environment_agent_resource_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_agent_resource_id_idx ON public.resource_persistent_state USING btree (environment, agent, resource_id);


--
-- Name: resource_persistent_state_environment_orphaned_after_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_orphaned_after_index ON public.resource_persistent_state USING btree (environment) WHERE (orphaned_after IS NULL);


--
-- Name: resource_persistent_state_environment_resource_id_orphaned_afte; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_id_orphaned_afte ON public.resource_persistent_state USING btree (environment, resource_id, orphaned_after);


--
-- Name: resource_persistent_state_environment_resource_id_value_res_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_id_value_res_idx ON public.resource_persistent_state USING btree (environment, resource_id_value, resource_id);


--
-- Name: resource_persistent_state_environment_resource_type_resourc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_type_resourc_idx ON public.resource_persistent_state USING btree (environment, resource_type, resource_id);


--
-- Name: resource_set_configuration_model_environment_resource_set_id_in; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_set_configuration_model_environment_resource_set_id_in ON public.resource_set_configuration_model USING btree (environment, resource_set);


--
-- Name: resource_set_environment_name_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_set_environment_name_id_index ON public.resource_set USING btree (environment, name, id);


--
-- Name: resourceaction_environment_action_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_action_started_index ON public.resourceaction USING btree (environment, action, started DESC);


--
-- Name: resourceaction_environment_version_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_version_started_index ON public.resourceaction USING btree (environment, version, started DESC);


--
-- Name: resourceaction_resource_environment_resource_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_resource_environment_resource_version_index ON public.resourceaction_resource USING btree (environment, resource_version);


--
-- Name: resourceaction_resource_resource_action_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_resource_resource_action_id_index ON public.resourceaction_resource USING btree (resource_action_id);


--
-- Name: resourceaction_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_started_index ON public.resourceaction USING btree (started);


--
-- Name: schedulersession_env_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX schedulersession_env_expired_index ON public.schedulersession USING btree (environment, expired);


--
-- Name: schedulersession_env_hostname_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX schedulersession_env_hostname_expired_index ON public.schedulersession USING btree (environment, hostname, expired);


--
-- Name: schedulersession_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX schedulersession_expired_index ON public.schedulersession USING btree (expired) WHERE (expired IS NULL);


--
-- Name: schedulersession_sid_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX schedulersession_sid_expired_index ON public.schedulersession USING btree (sid, expired);


--
-- Name: token_environment_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX token_environment_index ON public.token USING btree (environment);


--
-- Name: unknownparameter_env_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX unknownparameter_env_version_index ON public.unknownparameter USING btree (environment, version);


--
-- Name: unknownparameter_resolved_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX unknownparameter_resolved_index ON public.unknownparameter USING btree (resolved);


--
-- Name: agent agent_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_configurationmodel_modules_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_configurationmodel_modules_fkey FOREIGN KEY (environment, cm_version, inmanta_module_name) REFERENCES public.configurationmodel_modules(environment, cm_version, inmanta_module_name) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_environment_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_agent_name_fkey FOREIGN KEY (environment, agent_name) REFERENCES public.agent(environment, name) ON DELETE CASCADE;


--
-- Name: schedulersession agentprocess_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedulersession
    ADD CONSTRAINT agentprocess_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: compile compile_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: compile compile_substitute_compile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_substitute_compile_id_fkey FOREIGN KEY (substitute_compile_id) REFERENCES public.compile(id) ON DELETE CASCADE;


--
-- Name: configurationmodel configurationmodel_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel
    ADD CONSTRAINT configurationmodel_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: configurationmodel_modules configurationmodel_modules_configurationmodel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_configurationmodel_fkey FOREIGN KEY (environment, cm_version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: configurationmodel_modules configurationmodel_modules_inmanta_module_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_inmanta_module_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT;


--
-- Name: dryrun dryrun_environment_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun
    ADD CONSTRAINT dryrun_environment_model_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: environment environment_project_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environment
    ADD CONSTRAINT environment_project_fkey FOREIGN KEY (project) REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: environmentmetricsgauge environmentmetricsgauge_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricsgauge
    ADD CONSTRAINT environmentmetricsgauge_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: environmentmetricstimer environmentmetricstimer_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.environmentmetricstimer
    ADD CONSTRAINT environmentmetricstimer_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: inmanta_module inmanta_module_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_module
    ADD CONSTRAINT inmanta_module_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: module_files module_files_environment_inmanta_module_name_inmanta_modul_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.module_files
    ADD CONSTRAINT module_files_environment_inmanta_module_name_inmanta_modul_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE CASCADE;


--
-- Name: module_files module_files_file_content_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.module_files
    ADD CONSTRAINT module_files_file_content_hash_fkey FOREIGN KEY (file_content_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT;


--
-- Name: notification notification_compile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_compile_id_fkey FOREIGN KEY (compile_id) REFERENCES public.compile(id) ON DELETE CASCADE;


--
-- Name: notification notification_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: parameter parameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parameter
    ADD CONSTRAINT parameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: report report_compile_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report
    ADD CONSTRAINT report_compile_fkey FOREIGN KEY (compile) REFERENCES public.compile(id) ON DELETE CASCADE;


--
-- Name: resource_diff resource_diff_environment_resource_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_diff
    ADD CONSTRAINT resource_diff_environment_resource_id_fkey FOREIGN KEY (environment, resource_id) REFERENCES public.resource_persistent_state(environment, resource_id) ON DELETE CASCADE;


--
-- Name: resource_persistent_state resource_persistent_state_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_persistent_state
    ADD CONSTRAINT resource_persistent_state_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: resource_persistent_state resource_persistent_state_non_compliant_diff_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_persistent_state
    ADD CONSTRAINT resource_persistent_state_non_compliant_diff_fkey FOREIGN KEY (non_compliant_diff) REFERENCES public.resource_diff(id) ON DELETE RESTRICT;


--
-- Name: resource resource_resource_set_id_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_resource_set_id_environment_fkey FOREIGN KEY (resource_set, environment) REFERENCES public.resource_set(id, environment) ON DELETE CASCADE;


--
-- Name: resource_set_configuration_model resource_set_configuration_mod_environment_resource_set_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_set_configuration_model
    ADD CONSTRAINT resource_set_configuration_mod_environment_resource_set_id_fkey FOREIGN KEY (environment, resource_set) REFERENCES public.resource_set(environment, id);


--
-- Name: resource_set_configuration_model resource_set_configuration_model_environment_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_set_configuration_model
    ADD CONSTRAINT resource_set_configuration_model_environment_model_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resource_set resource_set_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_set
    ADD CONSTRAINT resource_set_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: resourceaction resourceaction_environment_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_environment_version_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction_resource resourceaction_resource_resource_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_resource_action_id_fkey FOREIGN KEY (resource_action_id) REFERENCES public.resourceaction(action_id) ON DELETE CASCADE;


--
-- Name: role_assignment role_assignment_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment
    ADD CONSTRAINT role_assignment_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: role_assignment role_assignment_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment
    ADD CONSTRAINT role_assignment_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id) ON DELETE RESTRICT;


--
-- Name: role_assignment role_assignment_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_assignment
    ADD CONSTRAINT role_assignment_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.inmanta_user(id) ON DELETE CASCADE;


--
-- Name: scheduler scheduler_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduler
    ADD CONSTRAINT scheduler_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: token token_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token
    ADD CONSTRAINT token_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- Name: unknownparameter unknownparameter_environment_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unknownparameter
    ADD CONSTRAINT unknownparameter_environment_version_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: discoveredresource unmanagedresource_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discoveredresource
    ADD CONSTRAINT unmanagedresource_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

