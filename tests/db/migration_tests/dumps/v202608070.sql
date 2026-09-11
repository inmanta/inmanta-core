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
    inmanta_module_version character varying NOT NULL,
    environment uuid NOT NULL,
    load_module_on_agent boolean
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
    setup_cfg_hash character varying,
    pyproject_toml_hash character varying,
    install_mode character varying NOT NULL
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
84bd8eba-1f3f-44fe-80f1-5b63294e818f	$__scheduler	f	\N
62919084-aac4-41e6-807b-63c1e1b2746b	$__scheduler	f	\N
610200e3-1232-4f03-8409-93735fcd554b	$__scheduler	f	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	internal	f	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	localhost	f	\N
62919084-aac4-41e6-807b-63c1e1b2746b	internal	f	\N
62919084-aac4-41e6-807b-63c1e1b2746b	localhost	f	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	agent3	f	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	agent2	f	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	agent1	t	t
f57c1351-cdaa-4178-9fe6-ac94f35d0410	$__scheduler	t	t
de6bcb66-7dd6-4bd7-82d3-c223eaa4de55	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, inmanta_module_version, environment, load_module_on_agent) FROM stdin;
1	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
1	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
1	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
1	internal	std	7.0.0	62919084-aac4-41e6-807b-63c1e1b2746b	t
1	localhost	fs	1.2.0	62919084-aac4-41e6-807b-63c1e1b2746b	t
2	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
2	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
2	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
3	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
3	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
3	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
4	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
4	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
4	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
5	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
5	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
5	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
6	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
6	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
6	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
7	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
7	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
7	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
8	internal	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
8	localhost	std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
8	localhost	fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	t
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:31:29.948008+02	2026-08-07 17:31:45.910556+02	2026-08-07 17:31:29.93844+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	10960cfc-8fbe-4b9f-8b2f-83ff646491ee	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
65df7a4e-03bd-4edd-9989-2993bbe515b7	62919084-aac4-41e6-807b-63c1e1b2746b	2026-08-07 17:31:46.094629+02	2026-08-07 17:32:00.381159+02	2026-08-07 17:31:46.078333+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	c80464b4-b55f-480b-a601-6fc6425bcda3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a960c232-eb5a-4526-94c6-fb54810647ed	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:00.57006+02	2026-08-07 17:32:01.76925+02	2026-08-07 17:32:00.566351+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	862299d0-76d9-4634-a76c-e04964f11e51	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
74077802-456e-4e6d-8d10-e0b3499ee6ae	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:01.870405+02	2026-08-07 17:32:03.050717+02	2026-08-07 17:32:01.851217+02	{}	{"add_one_resource": "true"}	t	f	t	3	353cb965-5446-4904-a2a0-4e24beafdf67	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
aae7f304-9538-4a92-9624-068d77703b13	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:03.315495+02	2026-08-07 17:32:04.534962+02	2026-08-07 17:32:03.301203+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	a23d74b5-f3a4-44b0-8b30-b0dc8142df01	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
5fe8ca1a-3559-4bd9-8e2b-81cb8289a3bf	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:04.637632+02	2026-08-07 17:32:05.918558+02	2026-08-07 17:32:04.607444+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	87bc8bba-68be-4d0a-8a3f-3e1449492bbd	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6a56ae61-6ed9-4a83-a251-487ece58f84c	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:06.065893+02	2026-08-07 17:32:19.277025+02	2026-08-07 17:32:06.052522+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	67836250-0c3c-4a29-974c-7cf2a470bd1e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
e212f1a9-1d06-4d25-abfa-79f8a97a881e	de6bcb66-7dd6-4bd7-82d3-c223eaa4de55	2026-08-07 17:32:20.082546+02	2026-08-07 17:32:20.090837+02	2026-08-07 17:32:20.06667+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	4d6bdf56-3326-43a2-afdd-cf2f5ee5d410	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:31:45.599087+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:19.496108+02	t	\N	3	{}	{}	7	t	\N	\N
1	62919084-aac4-41e6-807b-63c1e1b2746b	2026-08-07 17:32:00.10216+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:01.491805+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:02.749807+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:04.24976+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:05.624921+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:19.003606+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2026-08-07 17:32:19.683277+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:32:19.318462+02	t	\N	4	{}	{}	6	t	\N	\N
2	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2026-08-07 17:32:19.818955+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2026-08-07 17:32:19.943803+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
84bd8eba-1f3f-44fe-80f1-5b63294e818f	discovery::Discovered[myagent,name=discovered]	{}	2026-08-07 17:32:19.947309+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
84bd8eba-1f3f-44fe-80f1-5b63294e818f	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-08-07 17:32:19.947329+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
7346c5cb-8b25-4b75-91c6-17beb361e3d5	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	2026-08-07 17:32:19.80732+02	6	0	{"05c33762-10ca-5f44-849a-51230171c73f": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "0b497fcb-fd41-5d8f-b42d-3daa20693700": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "adf0fde5-5840-54f7-baf0-7f9773e6676a": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "cd5cbc90-94b4-5fe3-8b7e-12af792141e0": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "d33b8c93-c45f-5a7f-bfef-c1221f8db2e3": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "e72cd416-e03b-5c8d-bbe7-d4b1ddcaff52": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
f57c1351-cdaa-4178-9fe6-ac94f35d0410	dev-3	97b95121-41cb-4f5b-ae06-ab984594e589			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
84bd8eba-1f3f-44fe-80f1-5b63294e818f	dev-1	97b95121-41cb-4f5b-ae06-ab984594e589			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
62919084-aac4-41e6-807b-63c1e1b2746b	dev-1-twin	97b95121-41cb-4f5b-ae06-ab984594e589			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
de6bcb66-7dd6-4bd7-82d3-c223eaa4de55	dev-4	97b95121-41cb-4f5b-ae06-ab984594e589			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
610200e3-1232-4f03-8409-93735fcd554b	dev-2	97b95121-41cb-4f5b-ae06-ab984594e589			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
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

COPY public.inmanta_module (name, version, environment, requirements, setup_cfg_hash, pyproject_toml_hash, install_mode) FROM stdin;
std	8.7.4	84bd8eba-1f3f-44fe-80f1-5b63294e818f	\N	\N	\N	package
fs	1.2.0	84bd8eba-1f3f-44fe-80f1-5b63294e818f	\N	\N	\N	package
std	7.0.0	62919084-aac4-41e6-807b-63c1e1b2746b	\N	\N	\N	package
fs	1.2.0	62919084-aac4-41e6-807b-63c1e1b2746b	\N	\N	\N	package
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
5ee483d0-1377-4ced-88d5-14d626c08d3a	de6bcb66-7dd6-4bd7-82d3-c223eaa4de55	2026-08-07 17:32:20.096952+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/e212f1a9-1d06-4d25-abfa-79f8a97a881e	f	f	e212f1a9-1d06-4d25-abfa-79f8a97a881e
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
8f2052ec-049e-4147-924f-85f6f365b308	fact1	value1	84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::testing::NullResource[localhost,name=test1]	fact	2026-08-07 17:32:04.589185+02	{}	f
e0004a95-8d76-480b-ba56-893838ce94d3	fact2	value2	84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::testing::NullResource[localhost,name=test2]	fact	2026-08-07 17:32:04.594404+02	{}	t
557290cb-2573-4982-b6ef-3c4f78116b4e	fact3	value3	84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::testing::NullResource[localhost,name=test3]	fact	2026-08-07 17:32:04.597576+02	{}	t
a68457a6-d189-4328-aa93-9bf1c532736e	parameter1	value1	84bd8eba-1f3f-44fe-80f1-5b63294e818f		fact	2026-08-07 17:32:04.600292+02	{}	f
dea0628e-eaae-4448-a8fc-7625bf7d8b70	parameter2	value2	84bd8eba-1f3f-44fe-80f1-5b63294e818f		fact	2026-08-07 17:32:04.602774+02	{}	f
07ead52f-a585-4177-acee-9d913893fbfe	parameter3	value3	84bd8eba-1f3f-44fe-80f1-5b63294e818f		fact	2026-08-07 17:32:04.605238+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
97b95121-41cb-4f5b-ae06-ab984594e589	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
68cb96cb-8841-438b-8df9-81d715968b49	2026-08-07 17:31:29.948655+02	2026-08-07 17:31:29.951576+02		Init		Using extra environment variables during compile \n	0	ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d
3019fa3e-e078-4a81-99a2-b144e5f8ab44	2026-08-07 17:31:29.951833+02	2026-08-07 17:31:29.961494+02		Venv check		Creating new venv at /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env-py3.13\n	0	ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d
5aeb24dd-2810-4a25-956d-98fa05f65e35	2026-08-07 17:31:29.963139+02	2026-08-07 17:31:30.280485+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d
d8c5b60b-2507-4173-b0d8-73c7b71ce90a	2026-08-07 17:32:06.068712+02	2026-08-07 17:32:06.074289+02		Init		Using extra environment variables during compile \n	0	6a56ae61-6ed9-4a83-a251-487ece58f84c
9c0ebe74-3b4d-47aa-8e2b-bf121c317c44	2026-08-07 17:32:06.0747+02	2026-08-07 17:32:06.075323+02		Venv check		Found existing venv\n	0	6a56ae61-6ed9-4a83-a251-487ece58f84c
87f4bff3-269a-42fd-be62-d86444a00fc5	2026-08-07 17:32:06.076666+02	2026-08-07 17:32:06.400835+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6a56ae61-6ed9-4a83-a251-487ece58f84c
835f8199-3afe-411c-8b29-6f8ee3ca6f7b	2026-08-07 17:31:30.281209+02	2026-08-07 17:31:44.686992+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpgqnxp0n0:\n                                 Pip command: /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpgqnxp0n0 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.10.1)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached colorlog-6.12.0-py3-none-any.whl (12 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.1.2)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading pip-26.2.1-py3-none-any.whl (1.8 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 6.3 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.7)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading tornado-6.5.8-cp39-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (450 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.0)\ninmanta.pip              DEBUG   Collecting cffi>=2.0.0 (from cryptography<50,>=36->inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (221 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.51-py2.py3-none-any.whl (292 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.4.3)\ninmanta.pip              DEBUG   Collecting chardet<8,>=3.0.2 (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading chardet-7.5.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (959 kB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 959.6/959.6 kB 14.1 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, pip, mitogen, colorlog, chardet, cffi, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.7\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.1.2\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.10.1\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 7.4.3\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cffi\ninmanta.pip              DEBUG   Found existing installation: cffi 2.1.0\ninmanta.pip              DEBUG   Not uninstalling cffi at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cffi'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed cffi-2.1.1 chardet-7.5.1 colorlog-6.12.0 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.51 pip-26.2.1 tornado-6.5.8\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d
a5ee8c67-45d6-48e3-867b-3acb9fee768f	2026-08-07 17:31:44.687428+02	2026-08-07 17:31:45.909563+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp0u6ak7wv --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.019 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.025 seconds\ncompiler       DEBUG   The entire export command took 0.075 seconds\n	0	ff873dfb-7ffe-4599-a4d9-8a7d7c29ae3d
de3eef36-87b6-465d-8078-b7edba8ca2f8	2026-08-07 17:31:46.094982+02	2026-08-07 17:31:46.097754+02		Init		Using extra environment variables during compile \n	0	65df7a4e-03bd-4edd-9989-2993bbe515b7
bf8229ed-925d-429a-bfa3-73fb3fea9480	2026-08-07 17:31:46.098279+02	2026-08-07 17:31:46.109558+02		Venv check		Creating new venv at /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env-py3.13\n	0	65df7a4e-03bd-4edd-9989-2993bbe515b7
574d4dc7-1cac-4280-bb98-3c937e076627	2026-08-07 17:31:46.111656+02	2026-08-07 17:31:46.42655+02	/tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	65df7a4e-03bd-4edd-9989-2993bbe515b7
25ce7f7b-7766-4268-bdda-22f8d24238f0	2026-08-07 17:31:46.427218+02	2026-08-07 17:31:59.195736+02	/tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpxgjc3f9f:\n                                 Pip command: /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpxgjc3f9f inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.10.1)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached colorlog-6.12.0-py3-none-any.whl (12 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.1.2)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.2.1-py3-none-any.whl (1.8 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.7)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.5.8-cp39-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (450 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.0)\ninmanta.pip              DEBUG   Collecting cffi>=2.0.0 (from cryptography<50,>=36->inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached cffi-2.1.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (221 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.51-py2.py3-none-any.whl (292 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.4.3)\ninmanta.pip              DEBUG   Collecting chardet<8,>=3.0.2 (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached chardet-7.5.1-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (959 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, pip, mitogen, colorlog, chardet, cffi, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.7\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.1.2\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.10.1\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 7.4.3\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cffi\ninmanta.pip              DEBUG   Found existing installation: cffi 2.1.0\ninmanta.pip              DEBUG   Not uninstalling cffi at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cffi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed cffi-2.1.1 chardet-7.5.1 colorlog-6.12.0 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.51 pip-26.2.1 tornado-6.5.8\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	65df7a4e-03bd-4edd-9989-2993bbe515b7
ce1ff911-8cbc-442e-8335-a39e1121cb9a	2026-08-07 17:32:04.639068+02	2026-08-07 17:32:04.646456+02		Init		Using extra environment variables during compile \n	0	5fe8ca1a-3559-4bd9-8e2b-81cb8289a3bf
d49839e2-b749-48e3-b47d-ca54033f12c9	2026-08-07 17:31:59.196374+02	2026-08-07 17:32:00.380131+02	/tmp/tmpjzif234v/server/62919084-aac4-41e6-807b-63c1e1b2746b/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 62919084-aac4-41e6-807b-63c1e1b2746b --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpxrsz0sv5 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	65df7a4e-03bd-4edd-9989-2993bbe515b7
e190949b-0ade-434a-b78b-8b80c54e197c	2026-08-07 17:32:00.570568+02	2026-08-07 17:32:00.572735+02		Init		Using extra environment variables during compile \n	0	a960c232-eb5a-4526-94c6-fb54810647ed
03fff69b-96bd-4af8-b73f-6d57c014e68d	2026-08-07 17:32:00.573035+02	2026-08-07 17:32:00.573739+02		Venv check		Found existing venv\n	0	a960c232-eb5a-4526-94c6-fb54810647ed
eb6d6344-039d-44f1-8d15-6ab5fadab538	2026-08-07 17:32:04.647472+02	2026-08-07 17:32:04.649278+02		Venv check		Found existing venv\n	0	5fe8ca1a-3559-4bd9-8e2b-81cb8289a3bf
5ab915b8-c82e-4a14-ba42-8e233b28fb23	2026-08-07 17:32:00.574036+02	2026-08-07 17:32:01.768509+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpvxmlj5nd --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.021 seconds\ncompiler       DEBUG   The entire export command took 0.063 seconds\n	0	a960c232-eb5a-4526-94c6-fb54810647ed
807d2082-c928-4054-ad4a-003e6d6b9bba	2026-08-07 17:32:01.870997+02	2026-08-07 17:32:01.873868+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	74077802-456e-4e6d-8d10-e0b3499ee6ae
73644088-179d-4d51-b9bb-0749c759c951	2026-08-07 17:32:01.874353+02	2026-08-07 17:32:01.874975+02		Venv check		Found existing venv\n	0	74077802-456e-4e6d-8d10-e0b3499ee6ae
91c843f4-dbc2-4c3d-911f-f4fc1e5358e7	2026-08-07 17:32:01.875183+02	2026-08-07 17:32:03.049897+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmp4e9otqyv --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	74077802-456e-4e6d-8d10-e0b3499ee6ae
7165d0f8-1c9d-4f15-b17b-736917dd55af	2026-08-07 17:32:03.317241+02	2026-08-07 17:32:03.319731+02		Init		Using extra environment variables during compile \n	0	aae7f304-9538-4a92-9624-068d77703b13
82242f4b-9ef5-4873-b995-e7daf3314319	2026-08-07 17:32:03.320094+02	2026-08-07 17:32:03.320635+02		Venv check		Found existing venv\n	0	aae7f304-9538-4a92-9624-068d77703b13
360ecfff-fe82-46df-8051-39888f60c068	2026-08-07 17:32:03.320808+02	2026-08-07 17:32:04.533998+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpye2oer11 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.012 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.059 seconds\n	0	aae7f304-9538-4a92-9624-068d77703b13
28c60156-72a0-482c-985b-7c007b91e22a	2026-08-07 17:32:04.650108+02	2026-08-07 17:32:05.917735+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp4p4mas4a --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.057 seconds\n	0	5fe8ca1a-3559-4bd9-8e2b-81cb8289a3bf
5af557d8-1ea7-46e8-ad10-f2f89c390d73	2026-08-07 17:32:06.401618+02	2026-08-07 17:32:18.062402+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpqeutgb_j:\n                                 Pip command: /tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpqeutgb_j inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.13/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.13/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in ./.env/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.13/site-packages (from inmanta-module-mitogen) (0.3.51)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in ./.env/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	6a56ae61-6ed9-4a83-a251-487ece58f84c
218c85ca-8c97-4345-9507-0ef481110dfc	2026-08-07 17:32:18.063082+02	2026-08-07 17:32:19.276235+02	/tmp/tmpjzif234v/server/84bd8eba-1f3f-44fe-80f1-5b63294e818f/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 84bd8eba-1f3f-44fe-80f1-5b63294e818f --server_address localhost --server_port 49019 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpa5iyra6n --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:49019/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:49019/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	6a56ae61-6ed9-4a83-a251-487ece58f84c
8b543ce0-21a8-46bc-b964-3ca2eef1435a	2026-08-07 17:32:20.084043+02	2026-08-07 17:32:20.089246+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpjzif234v/server/de6bcb66-7dd6-4bd7-82d3-c223eaa4de55/compiler and no repository set.\n	1	e212f1a9-1d06-4d25-abfa-79f8a97a881e
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	71114357-1d59-4960-8be6-06c3c9070e2e
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	71114357-1d59-4960-8be6-06c3c9070e2e
62919084-aac4-41e6-807b-63c1e1b2746b	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	40923768-25bb-4a9e-a692-cbef2e97af0c
62919084-aac4-41e6-807b-63c1e1b2746b	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	40923768-25bb-4a9e-a692-cbef2e97af0c
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	f8ddb857-d877-4899-9c72-b0134889bdc9
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	f8ddb857-d877-4899-9c72-b0134889bdc9
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	3e14c56f-8f54-493c-9527-f02654197a81
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	3e14c56f-8f54-493c-9527-f02654197a81
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3e14c56f-8f54-493c-9527-f02654197a81
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	10793c44-e188-48bb-9e2f-0a9d1e63e2db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	10793c44-e188-48bb-9e2f-0a9d1e63e2db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	004554a2-9865-472d-8d61-596756c41366
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	004554a2-9865-472d-8d61-596756c41366
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	0be94cf9-9046-4392-84a1-eaa0d9b0d062
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0be94cf9-9046-4392-84a1-eaa0d9b0d062
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	e74f6ec7-387e-4840-9daa-3c5e2077d8fc
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e74f6ec7-387e-4840-9daa-3c5e2077d8fc
84bd8eba-1f3f-44fe-80f1-5b63294e818f	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	b4da0b55-3b3b-4458-998f-b11e0e1f2216
84bd8eba-1f3f-44fe-80f1-5b63294e818f	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	ea3f965c-b886-4769-9485-51fad1005336
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	58ae220b-8243-44c1-9446-64b7008da7db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	58ae220b-8243-44c1-9446-64b7008da7db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	7013fd66-2761-42a7-8fc8-427324be2310
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	4e2f4c59-2d27-4d7b-945f-049900e71057
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	4e2f4c59-2d27-4d7b-945f-049900e71057
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
e83f0598-7d15-4ff5-ab4c-2a88f7a69d77	f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-08-07 17:32:19.885447+02
818cb067-c43d-4b56-9175-b94e02f0a98c	f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-08-07 17:32:19.890003+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key10]	2026-08-07 17:32:19.885447+02	\N	2026-08-07 17:32:19.885447+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.825334+02	f	e83f0598-7d15-4ff5-ab4c-2a88f7a69d77	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key3]	2026-08-07 17:32:19.696486+02	\N	2026-08-07 17:32:19.696486+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-08-07 17:32:19.687044+02	f	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key1]	2026-08-07 17:32:19.701043+02	2026-08-07 17:32:19.697206+02	2026-08-07 17:32:19.701043+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.687044+02	t	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key11]	2026-08-07 17:32:19.890003+02	\N	2026-08-07 17:32:19.890003+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.825334+02	f	818cb067-c43d-4b56-9175-b94e02f0a98c	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	test::Resource[agent3,key=key3]	2026-08-07 17:32:19.361311+02	\N	2026-08-07 17:32:19.361311+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:19.345877+02	f	\N	7
62919084-aac4-41e6-807b-63c1e1b2746b	std::AgentConfig[internal,agentname=localhost]	2026-08-07 17:32:00.444594+02	\N	2026-08-07 17:32:00.444594+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:00.43824+02	f	\N	\N
62919084-aac4-41e6-807b-63c1e1b2746b	fs::File[localhost,path=/tmp/test]	2026-08-07 17:32:00.448375+02	\N	2026-08-07 17:32:00.448375+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:00.43824+02	f	\N	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	std::AgentConfig[internal,agentname=localhost]	2026-08-07 17:32:19.5661+02	\N	2026-08-07 17:32:19.5661+02	b8f697829071c376b6c9e448e5bd267d	8	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:31:45.940082+02	f	\N	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	test::Resource[agent2,key=key2]	2026-08-07 17:32:19.564725+02	\N	2026-08-07 17:32:19.564725+02	509af84c7d978674472e11ce2cad1b8b	8	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:19.345877+02	f	\N	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test]	2026-08-07 17:32:19.568943+02	\N	2026-08-07 17:32:19.568943+02	28b181a98279db3c2d85305e0c4d43c6	8	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:31:45.940082+02	f	\N	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	fs::File[localhost,path=/tmp/test_orphan]	2026-08-07 17:32:03.18405+02	\N	2026-08-07 17:32:03.18405+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:03.158165+02	f	\N	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-08-07 17:32:19.687044+02	\N	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-08-07 17:32:19.687044+02	\N	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key6]	2026-08-07 17:32:19.705879+02	2026-08-07 17:32:19.702199+02	2026-08-07 17:32:19.705879+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.687044+02	t	\N	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key9]	2026-08-07 17:32:19.872704+02	2026-08-07 17:32:19.867149+02	2026-08-07 17:32:19.872704+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.825334+02	t	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Resource[agent1,key=key7]	2026-08-07 17:32:19.878357+02	2026-08-07 17:32:19.874117+02	2026-08-07 17:32:19.878357+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-08-07 17:32:19.825334+02	t	\N	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	test::Fail[agent1,key=key2]	2026-08-07 17:32:19.881275+02	\N	2026-08-07 17:32:19.881275+02	fa7087083326c953261c388f13f3df3c	2	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-08-07 17:32:19.687044+02	f	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
84bd8eba-1f3f-44fe-80f1-5b63294e818f	71114357-1d59-4960-8be6-06c3c9070e2e	\N
62919084-aac4-41e6-807b-63c1e1b2746b	40923768-25bb-4a9e-a692-cbef2e97af0c	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	f8ddb857-d877-4899-9c72-b0134889bdc9	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	3e14c56f-8f54-493c-9527-f02654197a81	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	10793c44-e188-48bb-9e2f-0a9d1e63e2db	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	004554a2-9865-472d-8d61-596756c41366	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	0be94cf9-9046-4392-84a1-eaa0d9b0d062	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	e74f6ec7-387e-4840-9daa-3c5e2077d8fc	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	b4da0b55-3b3b-4458-998f-b11e0e1f2216	set-a
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ea3f965c-b886-4769-9485-51fad1005336	set-b
84bd8eba-1f3f-44fe-80f1-5b63294e818f	58ae220b-8243-44c1-9446-64b7008da7db	\N
84bd8eba-1f3f-44fe-80f1-5b63294e818f	7013fd66-2761-42a7-8fc8-427324be2310	set-a
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4b2f4bfb-e039-49e8-be97-60791a8e9704	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	13271d3b-415f-4740-9dc8-6d20636d6d12	\N
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4e2f4c59-2d27-4d7b-945f-049900e71057	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
84bd8eba-1f3f-44fe-80f1-5b63294e818f	1	71114357-1d59-4960-8be6-06c3c9070e2e
62919084-aac4-41e6-807b-63c1e1b2746b	1	40923768-25bb-4a9e-a692-cbef2e97af0c
84bd8eba-1f3f-44fe-80f1-5b63294e818f	2	f8ddb857-d877-4899-9c72-b0134889bdc9
84bd8eba-1f3f-44fe-80f1-5b63294e818f	3	3e14c56f-8f54-493c-9527-f02654197a81
84bd8eba-1f3f-44fe-80f1-5b63294e818f	4	10793c44-e188-48bb-9e2f-0a9d1e63e2db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	5	004554a2-9865-472d-8d61-596756c41366
84bd8eba-1f3f-44fe-80f1-5b63294e818f	6	0be94cf9-9046-4392-84a1-eaa0d9b0d062
84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	e74f6ec7-387e-4840-9daa-3c5e2077d8fc
84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	b4da0b55-3b3b-4458-998f-b11e0e1f2216
84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	ea3f965c-b886-4769-9485-51fad1005336
84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	58ae220b-8243-44c1-9446-64b7008da7db
84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	7013fd66-2761-42a7-8fc8-427324be2310
f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	4b2f4bfb-e039-49e8-be97-60791a8e9704
f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	13271d3b-415f-4740-9dc8-6d20636d6d12
f57c1351-cdaa-4178-9fe6-ac94f35d0410	3	4e2f4c59-2d27-4d7b-945f-049900e71057
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
ec3e4ed3-6ec2-4e94-8b81-87826ca7c6e5	store	2026-08-07 17:31:45.599031+02	2026-08-07 17:31:45.606268+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-08-07T17:31:45.606289+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
ae028c18-d115-4ee9-ad55-63758f96f55f	deploy	2026-08-07 17:31:45.946357+02	2026-08-07 17:31:45.95565+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:31:45.954815+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
74e10dce-607a-4768-b3ba-35284b96b70f	deploy	2026-08-07 17:31:45.959829+02	2026-08-07 17:31:45.961075+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:31:45.960623+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	1	{"fs::File[localhost,path=/tmp/test],v=1"}
3d6d7521-53c6-422a-b136-a200da9f2919	store	2026-08-07 17:32:00.102112+02	2026-08-07 17:32:00.104348+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-08-07T17:32:00.104356+02:00\\"}"}	\N	\N	\N	62919084-aac4-41e6-807b-63c1e1b2746b	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
cc5d9cdc-2e34-4bd0-b225-440b9cedbf2f	deploy	2026-08-07 17:32:00.44293+02	2026-08-07 17:32:00.444594+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:00.444101+02:00\\"}"}	unavailable	\N	nochange	62919084-aac4-41e6-807b-63c1e1b2746b	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
cdaf3162-9d0b-4cc9-b47e-f1f8094ec092	deploy	2026-08-07 17:32:00.447257+02	2026-08-07 17:32:00.448375+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:00.447956+02:00\\"}"}	unavailable	\N	nochange	62919084-aac4-41e6-807b-63c1e1b2746b	1	{"fs::File[localhost,path=/tmp/test],v=1"}
46f1994b-d20d-4f59-91a0-1873e98a028a	store	2026-08-07 17:32:01.491754+02	2026-08-07 17:32:01.497642+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-08-07T17:32:01.497652+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
c065e759-7434-491f-8d39-6f33ac6fc2f5	store	2026-08-07 17:32:02.749757+02	2026-08-07 17:32:02.752067+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-08-07T17:32:02.752075+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
d3af2799-1f3e-4810-8350-4ecce3f223cb	deploy	2026-08-07 17:32:03.168602+02	2026-08-07 17:32:03.172895+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=3: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=3\\"}, \\"timestamp\\": \\"2026-08-07T17:32:03.171970+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
8840fc98-7f9e-4261-b3cf-d944e50ae55e	deploy	2026-08-07 17:32:03.180379+02	2026-08-07 17:32:03.181932+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=3\\"}, \\"timestamp\\": \\"2026-08-07T17:32:03.181305+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	3	{"fs::File[localhost,path=/tmp/test],v=3"}
c72a20b9-4729-465a-8ff4-a2597d514fd9	deploy	2026-08-07 17:32:03.182965+02	2026-08-07 17:32:03.18405+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-08-07T17:32:03.183640+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
200fd943-22f8-4292-8c82-2c749927d026	store	2026-08-07 17:32:04.249715+02	2026-08-07 17:32:04.252147+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-08-07T17:32:04.252155+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	4	{"std::AgentConfig[internal,agentname=localhost],v=4","fs::File[localhost,path=/tmp/test],v=4"}
539d7bc7-ff76-4621-81eb-a284dbfa4486	deploy	2026-08-07 17:32:04.587823+02	2026-08-07 17:32:04.590009+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=4: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=4\\"}, \\"timestamp\\": \\"2026-08-07T17:32:04.589495+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	4	{"std::AgentConfig[internal,agentname=localhost],v=4"}
a3eec79a-731d-43b3-9004-34841466b635	deploy	2026-08-07 17:32:04.591371+02	2026-08-07 17:32:04.593565+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=4: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=4\\"}, \\"timestamp\\": \\"2026-08-07T17:32:04.593201+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	4	{"fs::File[localhost,path=/tmp/test],v=4"}
ad9afe20-38aa-4155-82a1-b04352e2d1c4	store	2026-08-07 17:32:05.624875+02	2026-08-07 17:32:05.630084+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-08-07T17:32:05.630095+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
603b1a3f-106a-4cff-af77-1bac84a80b3e	store	2026-08-07 17:32:19.003547+02	2026-08-07 17:32:19.006781+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-08-07T17:32:19.006806+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	6	{"fs::File[localhost,path=/tmp/test],v=6","std::AgentConfig[internal,agentname=localhost],v=6"}
def9a430-0790-490f-85f1-89f2b1436d32	deploy	2026-08-07 17:32:19.564813+02	2026-08-07 17:32:19.5661+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=8: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=8\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.565689+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	{"std::AgentConfig[internal,agentname=localhost],v=8"}
50c2d434-c3d2-4b83-af08-ec39fa781e5c	deploy	2026-08-07 17:32:19.559013+02	2026-08-07 17:32:19.564725+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=8: Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=8\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.564164+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	{"test::Resource[agent2,key=key2],v=8"}
9baa19a6-9067-4ba2-828d-f942173607f8	deploy	2026-08-07 17:32:19.691242+02	2026-08-07 17:32:19.694313+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 394253c0-9177-4cea-8c86-c71df2b3e1cb).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"394253c0-9177-4cea-8c86-c71df2b3e1cb\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.692128+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2652, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.693388+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 394253c0-9177-4cea-8c86-c71df2b3e1cb) - duration: 0.0021 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0021011829376220703, \\"deploy_id\\": \\"394253c0-9177-4cea-8c86-c71df2b3e1cb\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.694278+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}}}	nochange	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Fail[agent1,key=key2],v=1"}
a9aade8e-fd82-49cf-82af-247499fd9f69	deploy	2026-08-07 17:32:19.695676+02	2026-08-07 17:32:19.696486+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1f108e73-f618-4047-9a83-929bc24bd150).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"1f108e73-f618-4047-9a83-929bc24bd150\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.696289+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.696384+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 1f108e73-f618-4047-9a83-929bc24bd150) - duration: 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0001342296600341797, \\"deploy_id\\": \\"1f108e73-f618-4047-9a83-929bc24bd150\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.696460+02:00\\"}"}	skipped	\N	nochange	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key3],v=1"}
8dcfa2d5-ba4b-4ca5-84d8-4d3565dcad6c	deploy	2026-08-07 17:32:19.69723+02	2026-08-07 17:32:19.701043+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3fdadd28-d0bf-4d91-85be-fa5793270731).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"3fdadd28-d0bf-4d91-85be-fa5793270731\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.697775+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 3fdadd28-d0bf-4d91-85be-fa5793270731) - duration: 0.0032 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.003198862075805664, \\"deploy_id\\": \\"3fdadd28-d0bf-4d91-85be-fa5793270731\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.701015+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}}}	created	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key1],v=1"}
6c038b71-05be-4507-96ba-c025929bb8d1	store	2026-08-07 17:32:19.318369+02	2026-08-07 17:32:19.3226+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-08-07T17:32:19.322609+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	{"std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent3,key=key3],v=7","test::Resource[agent2,key=key2],v=7"}
febf03b4-ccc3-4ce3-9e6c-c87595e54b37	deploy	2026-08-07 17:32:19.358287+02	2026-08-07 17:32:19.359907+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.359112+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	{"test::Resource[agent2,key=key2],v=7"}
e21522e8-f2e1-45b7-b683-cb69d8071aba	deploy	2026-08-07 17:32:19.348877+02	2026-08-07 17:32:19.35823+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=7: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=7\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.357739+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	{"std::AgentConfig[internal,agentname=localhost],v=7"}
91af5a92-c8a4-423c-b351-74dc3f7792c6	deploy	2026-08-07 17:32:19.364976+02	2026-08-07 17:32:19.366001+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=7: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=7\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.365635+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	{"fs::File[localhost,path=/tmp/test],v=7"}
afc72d09-dbf9-4c37-bf83-90ff461a602d	deploy	2026-08-07 17:32:19.359967+02	2026-08-07 17:32:19.361311+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.360865+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	7	{"test::Resource[agent3,key=key3],v=7"}
326f4546-7e0f-4f05-ab13-5014315c3e44	store	2026-08-07 17:32:19.495491+02	2026-08-07 17:32:19.528659+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-08-07T17:32:19.528678+02:00\\"}"}	\N	\N	\N	84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	{"fs::File[localhost,path=/tmp/test],v=8","std::AgentConfig[internal,agentname=localhost],v=8","test::Resource[agent2,key=key2],v=8"}
989df006-a6bb-4d6b-9384-4048a3318c24	deploy	2026-08-07 17:32:19.567709+02	2026-08-07 17:32:19.568943+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=8: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=8\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.568580+02:00\\"}"}	unavailable	\N	nochange	84bd8eba-1f3f-44fe-80f1-5b63294e818f	8	{"fs::File[localhost,path=/tmp/test],v=8"}
97023289-47d5-41ce-8c98-62bf45a4563b	store	2026-08-07 17:32:19.683227+02	2026-08-07 17:32:19.685058+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-08-07T17:32:19.685067+02:00\\"}"}	\N	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key1],v=1"}
4a0b63b5-3261-46c8-b69c-ab49805e3ca8	store	2026-08-07 17:32:19.818888+02	2026-08-07 17:32:19.822012+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-08-07T17:32:19.822018+02:00\\"}"}	\N	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key1],v=2"}
82071977-26c9-405d-b007-dbd604a96793	dryrun	2026-08-07 17:32:19.822543+02	2026-08-07 17:32:19.82277+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.822583+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5 - duration 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00013899803161621094, \\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.822758+02:00\\"}"}	dry	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key6],v=1"}
e3d83395-6148-4966-83d5-bf724622a9e4	deploy	2026-08-07 17:32:19.867206+02	2026-08-07 17:32:19.872704+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 818834e5-b604-43c2-83f5-862720e4b68f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"818834e5-b604-43c2-83f5-862720e4b68f\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.868350+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 818834e5-b604-43c2-83f5-862720e4b68f) - duration: 0.0042 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.004228830337524414, \\"deploy_id\\": \\"818834e5-b604-43c2-83f5-862720e4b68f\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.872643+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}}}	created	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Resource[agent1,key=key9],v=2"}
fc5b8cac-515b-49ac-af9c-1ca57f99553a	deploy	2026-08-07 17:32:19.702233+02	2026-08-07 17:32:19.705879+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 739382df-d054-45cc-997c-196f02ca8b8f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"739382df-d054-45cc-997c-196f02ca8b8f\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.702936+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 739382df-d054-45cc-997c-196f02ca8b8f) - duration: 0.0028 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.002822399139404297, \\"deploy_id\\": \\"739382df-d054-45cc-997c-196f02ca8b8f\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.705826+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}}}	created	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key6],v=1"}
3febfb97-e3a9-4243-89f3-390b40cfe501	dryrun	2026-08-07 17:32:19.809985+02	2026-08-07 17:32:19.810364+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.810039+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00026154518127441406, \\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.810349+02:00\\"}"}	dry	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Fail[agent1,key=key2],v=1"}
a2135c34-c819-4b99-9801-2672eff4c6e9	dryrun	2026-08-07 17:32:19.814631+02	2026-08-07 17:32:19.814921+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.814675+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00019073486328125, \\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.814908+02:00\\"}"}	dry	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key1],v=1"}
76473a17-0a5f-4d54-ae5e-c0a69d99f68d	dryrun	2026-08-07 17:32:19.817893+02	2026-08-07 17:32:19.81819+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.817939+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00020241737365722656, \\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.818177+02:00\\"}"}	dry	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key3],v=1"}
42f7d652-5cdf-4b72-b789-f7c7f90f3eb0	dryrun	2026-08-07 17:32:19.820304+02	2026-08-07 17:32:19.820619+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.820347+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 7346c5cb-8b25-4b75-91c6-17beb361e3d5 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002219676971435547, \\"dry_run_id\\": \\"7346c5cb-8b25-4b75-91c6-17beb361e3d5\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.820607+02:00\\"}"}	dry	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	1	{"test::Resource[agent1,key=key5],v=1"}
c906034b-b97b-4d40-9a25-d51c7f3e8cb6	store	2026-08-07 17:32:19.943759+02	2026-08-07 17:32:19.945391+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-08-07T17:32:19.945401+02:00\\"}"}	\N	\N	\N	f57c1351-cdaa-4178-9fe6-ac94f35d0410	3	{"test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3"}
99d9bcfa-cbba-4bf6-b4cc-8ec3527f97b4	deploy	2026-08-07 17:32:19.874157+02	2026-08-07 17:32:19.878357+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 84e257c4-f770-4e3d-bd18-271c030a1d12).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"84e257c4-f770-4e3d-bd18-271c030a1d12\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.874947+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 84e257c4-f770-4e3d-bd18-271c030a1d12) - duration: 0.0033 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0032830238342285156, \\"deploy_id\\": \\"84e257c4-f770-4e3d-bd18-271c030a1d12\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.878302+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}}}	created	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Resource[agent1,key=key7],v=2"}
3f840449-a801-4675-a202-fd1bd5c158f5	deploy	2026-08-07 17:32:19.879623+02	2026-08-07 17:32:19.881275+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f4fc713e-918e-486d-a0b7-f28323815861).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"f4fc713e-918e-486d-a0b7-f28323815861\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.880290+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2652, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.880734+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=2. (deploy_id: f4fc713e-918e-486d-a0b7-f28323815861) - duration: 0.0009 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=2\\", \\"duration\\": 0.0009233951568603516, \\"deploy_id\\": \\"f4fc713e-918e-486d-a0b7-f28323815861\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.881250+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=2": {"value": {"current": null, "desired": "val2"}}}	nochange	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Fail[agent1,key=key2],v=2"}
5063ea38-cbcf-42dd-bca9-684ff825a5bf	deploy	2026-08-07 17:32:19.882206+02	2026-08-07 17:32:19.885447+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: dc19769b-fdf6-4bac-a474-308b37039804).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"dc19769b-fdf6-4bac-a474-308b37039804\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.882816+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.882943+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: dc19769b-fdf6-4bac-a474-308b37039804) - duration: 0.0026 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0025577545166015625, \\"deploy_id\\": \\"dc19769b-fdf6-4bac-a474-308b37039804\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.885416+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}}}	nochange	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Resource[agent1,key=key10],v=2"}
50aa0c14-126b-4e10-8486-9220bfd89d5c	deploy	2026-08-07 17:32:19.886911+02	2026-08-07 17:32:19.890003+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: bb1f5c74-fec7-4f3e-b62c-390a1e0bf384).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"bb1f5c74-fec7-4f3e-b62c-390a1e0bf384\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.887526+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.887649+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: bb1f5c74-fec7-4f3e-b62c-390a1e0bf384) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.002405405044555664, \\"deploy_id\\": \\"bb1f5c74-fec7-4f3e-b62c-390a1e0bf384\\"}, \\"timestamp\\": \\"2026-08-07T17:32:19.889974+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}}}	nochange	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2	{"test::Resource[agent1,key=key11],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ec3e4ed3-6ec2-4e94-8b81-87826ca7c6e5	std::AgentConfig[internal,agentname=localhost]	1
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ec3e4ed3-6ec2-4e94-8b81-87826ca7c6e5	fs::File[localhost,path=/tmp/test]	1
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ae028c18-d115-4ee9-ad55-63758f96f55f	std::AgentConfig[internal,agentname=localhost]	1
84bd8eba-1f3f-44fe-80f1-5b63294e818f	74e10dce-607a-4768-b3ba-35284b96b70f	fs::File[localhost,path=/tmp/test]	1
62919084-aac4-41e6-807b-63c1e1b2746b	3d6d7521-53c6-422a-b136-a200da9f2919	std::AgentConfig[internal,agentname=localhost]	1
62919084-aac4-41e6-807b-63c1e1b2746b	3d6d7521-53c6-422a-b136-a200da9f2919	fs::File[localhost,path=/tmp/test]	1
62919084-aac4-41e6-807b-63c1e1b2746b	cc5d9cdc-2e34-4bd0-b225-440b9cedbf2f	std::AgentConfig[internal,agentname=localhost]	1
62919084-aac4-41e6-807b-63c1e1b2746b	cdaf3162-9d0b-4cc9-b47e-f1f8094ec092	fs::File[localhost,path=/tmp/test]	1
84bd8eba-1f3f-44fe-80f1-5b63294e818f	46f1994b-d20d-4f59-91a0-1873e98a028a	std::AgentConfig[internal,agentname=localhost]	2
84bd8eba-1f3f-44fe-80f1-5b63294e818f	46f1994b-d20d-4f59-91a0-1873e98a028a	fs::File[localhost,path=/tmp/test]	2
84bd8eba-1f3f-44fe-80f1-5b63294e818f	c065e759-7434-491f-8d39-6f33ac6fc2f5	fs::File[localhost,path=/tmp/test]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	c065e759-7434-491f-8d39-6f33ac6fc2f5	fs::File[localhost,path=/tmp/test_orphan]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	c065e759-7434-491f-8d39-6f33ac6fc2f5	std::AgentConfig[internal,agentname=localhost]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	d3af2799-1f3e-4810-8350-4ecce3f223cb	std::AgentConfig[internal,agentname=localhost]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	8840fc98-7f9e-4261-b3cf-d944e50ae55e	fs::File[localhost,path=/tmp/test]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	c72a20b9-4729-465a-8ff4-a2597d514fd9	fs::File[localhost,path=/tmp/test_orphan]	3
84bd8eba-1f3f-44fe-80f1-5b63294e818f	200fd943-22f8-4292-8c82-2c749927d026	std::AgentConfig[internal,agentname=localhost]	4
84bd8eba-1f3f-44fe-80f1-5b63294e818f	200fd943-22f8-4292-8c82-2c749927d026	fs::File[localhost,path=/tmp/test]	4
84bd8eba-1f3f-44fe-80f1-5b63294e818f	539d7bc7-ff76-4621-81eb-a284dbfa4486	std::AgentConfig[internal,agentname=localhost]	4
84bd8eba-1f3f-44fe-80f1-5b63294e818f	a3eec79a-731d-43b3-9004-34841466b635	fs::File[localhost,path=/tmp/test]	4
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ad9afe20-38aa-4155-82a1-b04352e2d1c4	std::AgentConfig[internal,agentname=localhost]	5
84bd8eba-1f3f-44fe-80f1-5b63294e818f	ad9afe20-38aa-4155-82a1-b04352e2d1c4	fs::File[localhost,path=/tmp/test]	5
84bd8eba-1f3f-44fe-80f1-5b63294e818f	603b1a3f-106a-4cff-af77-1bac84a80b3e	fs::File[localhost,path=/tmp/test]	6
84bd8eba-1f3f-44fe-80f1-5b63294e818f	603b1a3f-106a-4cff-af77-1bac84a80b3e	std::AgentConfig[internal,agentname=localhost]	6
84bd8eba-1f3f-44fe-80f1-5b63294e818f	6c038b71-05be-4507-96ba-c025929bb8d1	std::AgentConfig[internal,agentname=localhost]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	6c038b71-05be-4507-96ba-c025929bb8d1	fs::File[localhost,path=/tmp/test]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	6c038b71-05be-4507-96ba-c025929bb8d1	test::Resource[agent3,key=key3]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	6c038b71-05be-4507-96ba-c025929bb8d1	test::Resource[agent2,key=key2]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	e21522e8-f2e1-45b7-b683-cb69d8071aba	std::AgentConfig[internal,agentname=localhost]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	febf03b4-ccc3-4ce3-9e6c-c87595e54b37	test::Resource[agent2,key=key2]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	afc72d09-dbf9-4c37-bf83-90ff461a602d	test::Resource[agent3,key=key3]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	91af5a92-c8a4-423c-b351-74dc3f7792c6	fs::File[localhost,path=/tmp/test]	7
84bd8eba-1f3f-44fe-80f1-5b63294e818f	326f4546-7e0f-4f05-ab13-5014315c3e44	fs::File[localhost,path=/tmp/test]	8
84bd8eba-1f3f-44fe-80f1-5b63294e818f	326f4546-7e0f-4f05-ab13-5014315c3e44	std::AgentConfig[internal,agentname=localhost]	8
84bd8eba-1f3f-44fe-80f1-5b63294e818f	326f4546-7e0f-4f05-ab13-5014315c3e44	test::Resource[agent2,key=key2]	8
84bd8eba-1f3f-44fe-80f1-5b63294e818f	50c2d434-c3d2-4b83-af08-ec39fa781e5c	test::Resource[agent2,key=key2]	8
84bd8eba-1f3f-44fe-80f1-5b63294e818f	def9a430-0790-490f-85f1-89f2b1436d32	std::AgentConfig[internal,agentname=localhost]	8
84bd8eba-1f3f-44fe-80f1-5b63294e818f	989df006-a6bb-4d6b-9384-4048a3318c24	fs::File[localhost,path=/tmp/test]	8
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Resource[agent1,key=key5]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Fail[agent1,key=key2]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Resource[agent1,key=key6]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Resource[agent1,key=key3]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Resource[agent1,key=key4]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	97023289-47d5-41ce-8c98-62bf45a4563b	test::Resource[agent1,key=key1]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	9baa19a6-9067-4ba2-828d-f942173607f8	test::Fail[agent1,key=key2]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	a9aade8e-fd82-49cf-82af-247499fd9f69	test::Resource[agent1,key=key3]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	8dcfa2d5-ba4b-4ca5-84d8-4d3565dcad6c	test::Resource[agent1,key=key1]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	fc5b8cac-515b-49ac-af9c-1ca57f99553a	test::Resource[agent1,key=key6]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	3febfb97-e3a9-4243-89f3-390b40cfe501	test::Fail[agent1,key=key2]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	a2135c34-c819-4b99-9801-2672eff4c6e9	test::Resource[agent1,key=key1]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	76473a17-0a5f-4d54-ae5e-c0a69d99f68d	test::Resource[agent1,key=key3]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	42f7d652-5cdf-4b72-b789-f7c7f90f3eb0	test::Resource[agent1,key=key5]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key3]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key4]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key10]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key7]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key9]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key11]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key5]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Fail[agent1,key=key2]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	4a0b63b5-3261-46c8-b69c-ab49805e3ca8	test::Resource[agent1,key=key1]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	82071977-26c9-405d-b007-dbd604a96793	test::Resource[agent1,key=key6]	1
f57c1351-cdaa-4178-9fe6-ac94f35d0410	e3d83395-6148-4966-83d5-bf724622a9e4	test::Resource[agent1,key=key9]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	99d9bcfa-cbba-4bf6-b4cc-8ec3527f97b4	test::Resource[agent1,key=key7]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	3f840449-a801-4675-a202-fd1bd5c158f5	test::Fail[agent1,key=key2]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	5063ea38-cbcf-42dd-bca9-684ff825a5bf	test::Resource[agent1,key=key10]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	50aa0c14-126b-4e10-8486-9220bfd89d5c	test::Resource[agent1,key=key11]	2
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key8]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key3]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key1]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key4]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key7]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Resource[agent1,key=key5]	3
f57c1351-cdaa-4178-9fe6-ac94f35d0410	c906034b-b97b-4d40-9a25-d51c7f3e8cb6	test::Fail[agent1,key=key2]	3
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
62919084-aac4-41e6-807b-63c1e1b2746b	1
84bd8eba-1f3f-44fe-80f1-5b63294e818f	8
f57c1351-cdaa-4178-9fe6-ac94f35d0410	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	84bd8eba-1f3f-44fe-80f1-5b63294e818f	2026-08-07 17:31:29.691723+02	\N	a1ba578d-b0c1-4582-86ed-39d5755b0c99
hugo-Latitude-5421	62919084-aac4-41e6-807b-63c1e1b2746b	2026-08-07 17:31:29.806952+02	\N	05fcc2a9-0157-4fb7-b316-aadddc070849
hugo-Latitude-5421	f57c1351-cdaa-4178-9fe6-ac94f35d0410	2026-08-07 17:32:19.573641+02	2026-08-07 17:32:19.940143+02	7be94f79-c497-4016-9429-03b1a418fee8
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202607160,202608070}
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
    ADD CONSTRAINT agent_modules_pkey PRIMARY KEY (environment, cm_version, agent_name, inmanta_module_name);


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
-- Name: agent_modules_environment_module_name_module_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_modules_environment_module_name_module_version_index ON public.agent_modules USING btree (environment, inmanta_module_name, inmanta_module_version);


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
-- Name: agent_modules agent_modules_environment_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_agent_name_fkey FOREIGN KEY (environment, agent_name) REFERENCES public.agent(environment, name) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_environment_cm_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_cm_version_fkey FOREIGN KEY (environment, cm_version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_environment_inmanta_module_name_inmanta_modu_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_inmanta_module_name_inmanta_modu_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT;


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
-- Name: configurationmodel_modules configurationmodel_modules_environment_cm_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_environment_cm_version_fkey FOREIGN KEY (environment, cm_version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: configurationmodel_modules configurationmodel_modules_environment_inmanta_module_na_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_environment_inmanta_module_na_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT;


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
-- Name: inmanta_module inmanta_module_pyproject_toml_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_module
    ADD CONSTRAINT inmanta_module_pyproject_toml_hash_fkey FOREIGN KEY (pyproject_toml_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT;


--
-- Name: inmanta_module inmanta_module_setup_cfg_hash_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmanta_module
    ADD CONSTRAINT inmanta_module_setup_cfg_hash_fkey FOREIGN KEY (setup_cfg_hash) REFERENCES public.file(content_hash) ON DELETE RESTRICT;


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

