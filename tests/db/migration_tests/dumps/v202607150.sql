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
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	$__scheduler	f	\N
55d5ed9a-e173-43e6-9221-7fd46544cd1d	$__scheduler	f	\N
f68cd47d-78f2-4073-8f88-34034f20bdb3	$__scheduler	f	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	internal	f	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	localhost	f	\N
55d5ed9a-e173-43e6-9221-7fd46544cd1d	internal	f	\N
55d5ed9a-e173-43e6-9221-7fd46544cd1d	localhost	f	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	agent2	f	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	agent3	f	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	agent1	t	t
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	$__scheduler	t	t
e30c7032-ae66-4c8b-b004-2973f8943ee6	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, inmanta_module_version, environment, load_module_on_agent) FROM stdin;
1	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
1	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
1	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
1	internal	std	7.0.0	55d5ed9a-e173-43e6-9221-7fd46544cd1d	t
1	localhost	fs	1.2.0	55d5ed9a-e173-43e6-9221-7fd46544cd1d	t
2	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
2	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
2	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
3	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
3	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
3	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
4	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
4	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
4	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
5	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
5	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
5	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
6	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
6	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
6	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
7	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
7	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
7	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
8	internal	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
8	localhost	std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
8	localhost	fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	t
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
41417a3b-9bdb-4340-8699-9ab6291f1722	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:06.091189+02	2026-07-30 11:24:22.702815+02	2026-07-30 11:24:06.05663+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	033768d5-48aa-433d-b147-47b65be032e6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f5d25f38-9425-4d90-a5c3-44ec0f8274aa	55d5ed9a-e173-43e6-9221-7fd46544cd1d	2026-07-30 11:24:23.013988+02	2026-07-30 11:24:37.387078+02	2026-07-30 11:24:22.980526+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	854d1cca-812f-48ea-aab0-eb3b03cf2bb7	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
83b0a2c9-b589-4d4b-848c-ea3612115f6b	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:37.67081+02	2026-07-30 11:24:38.917101+02	2026-07-30 11:24:37.666021+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	1333933c-e748-4942-8bf2-884512423892	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f08a95ca-1be5-4750-a755-8cb451a13811	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:39.021157+02	2026-07-30 11:24:40.304871+02	2026-07-30 11:24:38.930219+02	{}	{"add_one_resource": "true"}	t	f	t	3	9399a919-5efa-43ea-8c7e-436c3b435835	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
fa696dc3-ad5d-48ac-9c5d-16f90bdb6b21	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:40.581432+02	2026-07-30 11:24:41.806621+02	2026-07-30 11:24:40.567305+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	3c63b3c7-ca75-403d-8fc2-1ea438cf62b9	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
fae3ca97-ce6c-4a59-ab0d-d4226036df99	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:41.907405+02	2026-07-30 11:24:43.099708+02	2026-07-30 11:24:41.879371+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	8af8f02f-de19-41df-9273-d3531119d67a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f12690c4-509a-4b2e-b555-82bfa2c7ad74	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:43.22315+02	2026-07-30 11:24:56.535177+02	2026-07-30 11:24:43.208039+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	4e05be7f-765a-49ea-bef4-1d5ccef3f72f	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
729e5f41-7b45-4a17-a0e7-2fa59f0b651c	e30c7032-ae66-4c8b-b004-2973f8943ee6	2026-07-30 11:24:57.499441+02	2026-07-30 11:24:57.511517+02	2026-07-30 11:24:57.484169+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	40a01060-2388-49c9-8657-21a6032f2eb8	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:22.403115+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:56.762817+02	t	\N	3	{}	{}	7	t	\N	\N
1	55d5ed9a-e173-43e6-9221-7fd46544cd1d	2026-07-30 11:24:37.08497+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:38.626859+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:40.003842+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:41.539111+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:42.825175+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:56.246427+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2026-07-30 11:24:56.968886+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:56.560221+02	t	\N	4	{}	{}	6	t	\N	\N
2	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2026-07-30 11:24:57.18276+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2026-07-30 11:24:57.359619+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	discovery::Discovered[myagent,name=discovered]	{}	2026-07-30 11:24:57.365391+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-07-30 11:24:57.365411+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
3ebc47b6-b9f0-4044-acd1-b102967d9518	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	2026-07-30 11:24:57.140155+02	6	0	{"09e55544-e3c6-5a6a-b99d-106ee2e97f4f": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "0b693bf6-0a08-5f00-a4b4-f29d3f0ef26f": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "17c646b5-8b3f-5b44-a817-f85ac0d76fa7": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "4b8693c4-878a-5cc2-831f-fee5c3f6c966": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "7952788b-f73d-5807-ba5d-d7f3fd41e68b": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "93d472c0-bf62-53c0-8012-fdaf028934c9": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	dev-3	f6dd6bc5-d1b5-4784-8854-15d344c9f6ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	dev-1	f6dd6bc5-d1b5-4784-8854-15d344c9f6ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
55d5ed9a-e173-43e6-9221-7fd46544cd1d	dev-1-twin	f6dd6bc5-d1b5-4784-8854-15d344c9f6ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
e30c7032-ae66-4c8b-b004-2973f8943ee6	dev-4	f6dd6bc5-d1b5-4784-8854-15d344c9f6ee			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
f68cd47d-78f2-4073-8f88-34034f20bdb3	dev-2	f6dd6bc5-d1b5-4784-8854-15d344c9f6ee			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
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
std	8.7.4	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	\N	f
fs	1.2.0	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	\N	f
std	7.0.0	55d5ed9a-e173-43e6-9221-7fd46544cd1d	\N	f
fs	1.2.0	55d5ed9a-e173-43e6-9221-7fd46544cd1d	\N	f
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
991c87e1-d55b-4956-8752-c7c5fdadb1cb	e30c7032-ae66-4c8b-b004-2973f8943ee6	2026-07-30 11:24:57.518219+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/729e5f41-7b45-4a17-a0e7-2fa59f0b651c	f	f	729e5f41-7b45-4a17-a0e7-2fa59f0b651c
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
8d457cf3-87d2-45cf-b50c-e53a444cd41d	fact1	value1	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::testing::NullResource[localhost,name=test1]	fact	2026-07-30 11:24:41.861799+02	{}	f
964191f4-683b-4f07-bfae-d37cd2b109bd	fact2	value2	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::testing::NullResource[localhost,name=test2]	fact	2026-07-30 11:24:41.866343+02	{}	t
aad2ce3a-1bfd-4626-878a-209f73dbfcf2	fact3	value3	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::testing::NullResource[localhost,name=test3]	fact	2026-07-30 11:24:41.868748+02	{}	t
d0f5ba22-d8c3-4247-98bd-252c1f5d96d0	parameter1	value1	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a		fact	2026-07-30 11:24:41.870981+02	{}	f
5d3b06eb-4f5d-4aba-ac88-9e27f4efd6e6	parameter2	value2	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a		fact	2026-07-30 11:24:41.873137+02	{}	f
15391e75-4fbc-46f4-a199-9ddac6919678	parameter3	value3	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a		fact	2026-07-30 11:24:41.875792+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
f6dd6bc5-d1b5-4784-8854-15d344c9f6ee	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
6ff17e0b-1d07-4461-9c44-8c9a8a7b1ce7	2026-07-30 11:24:06.092999+02	2026-07-30 11:24:06.102003+02		Init		Using extra environment variables during compile \n	0	41417a3b-9bdb-4340-8699-9ab6291f1722
f5574da9-89a7-42f6-b850-1b18204a7064	2026-07-30 11:24:06.103883+02	2026-07-30 11:24:06.128385+02		Venv check		Creating new venv at /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env-py3.13\n	0	41417a3b-9bdb-4340-8699-9ab6291f1722
1757116e-bd35-46f4-838f-75e5fe8fb701	2026-07-30 11:24:06.132763+02	2026-07-30 11:24:06.49275+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	41417a3b-9bdb-4340-8699-9ab6291f1722
0acfb01d-9eb3-4f82-a535-a139061facdf	2026-07-30 11:24:06.49351+02	2026-07-30 11:24:21.467871+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmppse2jajh:\n                                 Pip command: /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmppse2jajh inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.10.1)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading colorlog-6.12.0-py3-none-any.whl (12 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.1.2)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Downloading pip-26.2-py3-none-any.whl (1.8 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.8/1.8 MB 5.9 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.7)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.51-py2.py3-none-any.whl (292 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: pip, mitogen, colorlog, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.1.2\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.10.1\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed colorlog-6.12.0 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.51 pip-26.2\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	41417a3b-9bdb-4340-8699-9ab6291f1722
8b1bdb6f-68df-49d4-8005-a352bc5b16f8	2026-07-30 11:24:23.056869+02	2026-07-30 11:24:23.419212+02	/tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	f5d25f38-9425-4d90-a5c3-44ec0f8274aa
58989b49-b7c2-40c7-8c13-e26242b63c11	2026-07-30 11:24:37.671209+02	2026-07-30 11:24:37.67333+02		Init		Using extra environment variables during compile \n	0	83b0a2c9-b589-4d4b-848c-ea3612115f6b
8373c8cd-ce11-4263-8b14-86cf2ace61f2	2026-07-30 11:24:37.673605+02	2026-07-30 11:24:37.674071+02		Venv check		Found existing venv\n	0	83b0a2c9-b589-4d4b-848c-ea3612115f6b
ebbf2eed-3506-43f5-947b-be2f03685b25	2026-07-30 11:24:21.468542+02	2026-07-30 11:24:22.701952+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3z0jr7ja --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.025 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.079 seconds\n	0	41417a3b-9bdb-4340-8699-9ab6291f1722
4a4ff136-b8ba-4c42-92c7-da1759e4f97e	2026-07-30 11:24:23.015877+02	2026-07-30 11:24:23.024199+02		Init		Using extra environment variables during compile \n	0	f5d25f38-9425-4d90-a5c3-44ec0f8274aa
c6944822-ae78-429a-bec3-a37374069161	2026-07-30 11:24:23.02516+02	2026-07-30 11:24:23.051142+02		Venv check		Creating new venv at /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env-py3.13\n	0	f5d25f38-9425-4d90-a5c3-44ec0f8274aa
cd240438-9ebc-4322-bf40-81d36a2d8f09	2026-07-30 11:24:23.419653+02	2026-07-30 11:24:36.141309+02	/tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp5ic8_9qb:\n                                 Pip command: /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp5ic8_9qb inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.10.1)\ninmanta.pip              DEBUG   Collecting colorlog~=6.4 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached colorlog-6.12.0-py3-none-any.whl (12 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.1.2)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==19.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.2-py3-none-any.whl (1.8 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.7)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.51-py2.py3-none-any.whl (292 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: pip, mitogen, colorlog, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.1.2\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: colorlog\ninmanta.pip              DEBUG   Found existing installation: colorlog 6.10.1\ninmanta.pip              DEBUG   Not uninstalling colorlog at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'colorlog'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed colorlog-6.12.0 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.51 pip-26.2\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	f5d25f38-9425-4d90-a5c3-44ec0f8274aa
f37cfd21-c665-480b-943c-55ade4735de5	2026-07-30 11:24:36.142129+02	2026-07-30 11:24:37.386006+02	/tmp/tmphl8gbyv0/server/55d5ed9a-e173-43e6-9221-7fd46544cd1d/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 55d5ed9a-e173-43e6-9221-7fd46544cd1d --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpc2nord5_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.012 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.019 seconds\ncompiler       DEBUG   The entire export command took 0.060 seconds\n	0	f5d25f38-9425-4d90-a5c3-44ec0f8274aa
0a36f893-eef4-4fba-953f-df60c37059ee	2026-07-30 11:24:39.022703+02	2026-07-30 11:24:39.030411+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	f08a95ca-1be5-4750-a755-8cb451a13811
4e1788f0-501e-4eba-87e0-8af641c6bcd1	2026-07-30 11:24:39.03145+02	2026-07-30 11:24:39.033284+02		Venv check		Found existing venv\n	0	f08a95ca-1be5-4750-a755-8cb451a13811
5f1553bc-3ffb-4136-8c3e-51c5659022de	2026-07-30 11:24:37.674286+02	2026-07-30 11:24:38.915911+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpq7nh2avq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	83b0a2c9-b589-4d4b-848c-ea3612115f6b
ce23e169-1e3f-408a-8bf4-4ce2ff5e1c5d	2026-07-30 11:24:41.907776+02	2026-07-30 11:24:41.909794+02		Init		Using extra environment variables during compile \n	0	fae3ca97-ce6c-4a59-ab0d-d4226036df99
a4d329fd-23c2-4732-bb4d-90e7f577fa42	2026-07-30 11:24:41.910049+02	2026-07-30 11:24:41.910492+02		Venv check		Found existing venv\n	0	fae3ca97-ce6c-4a59-ab0d-d4226036df99
9fb92b26-227a-4e26-be49-52364681deb8	2026-07-30 11:24:39.034899+02	2026-07-30 11:24:40.304195+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpsq_we8u9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	f08a95ca-1be5-4750-a755-8cb451a13811
4443eaba-8dc6-4c6c-a493-561bc859b37a	2026-07-30 11:24:40.582474+02	2026-07-30 11:24:40.5845+02		Init		Using extra environment variables during compile \n	0	fa696dc3-ad5d-48ac-9c5d-16f90bdb6b21
80f43419-38c1-4ea8-a527-0221bbbc3a95	2026-07-30 11:24:40.584716+02	2026-07-30 11:24:40.585166+02		Venv check		Found existing venv\n	0	fa696dc3-ad5d-48ac-9c5d-16f90bdb6b21
ee923701-8ba5-4346-90e7-be0338dc761e	2026-07-30 11:24:40.585333+02	2026-07-30 11:24:41.805796+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1_t1f47w --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.017 seconds\ncompiler       DEBUG   The entire export command took 0.060 seconds\n	0	fa696dc3-ad5d-48ac-9c5d-16f90bdb6b21
0d6b9e66-b27f-42bc-ac48-ff8b98e0bb85	2026-07-30 11:24:41.910706+02	2026-07-30 11:24:43.098926+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1aw5ft1z --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	fae3ca97-ce6c-4a59-ab0d-d4226036df99
b8c86812-a6aa-4912-a2f4-77de82721d55	2026-07-30 11:24:43.226544+02	2026-07-30 11:24:43.231724+02		Init		Using extra environment variables during compile \n	0	f12690c4-509a-4b2e-b555-82bfa2c7ad74
c94724e3-f941-47fe-82d3-cb9a1e20e183	2026-07-30 11:24:43.232426+02	2026-07-30 11:24:43.233719+02		Venv check		Found existing venv\n	0	f12690c4-509a-4b2e-b555-82bfa2c7ad74
c66eb8d4-6bc3-414c-9f1d-9a9b6ca3b221	2026-07-30 11:24:43.236456+02	2026-07-30 11:24:43.587879+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 19.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	f12690c4-509a-4b2e-b555-82bfa2c7ad74
ebe98c78-55f5-4f3b-a69e-705c5de76220	2026-07-30 11:24:43.588496+02	2026-07-30 11:24:55.342578+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpg45tmpn1:\n                                 Pip command: /tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpg45tmpn1 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==19.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.13/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.13/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==19.0.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (19.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.5,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (8.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in ./.env/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<50,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (49.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.3,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (26.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (6.5.7)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.0.51)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.9,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (3.2.11)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==19.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==19.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<50,>=36->inmanta-core==19.0.0.dev0) (2.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==19.0.0.dev0) (3.18)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==19.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (2.46.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==19.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==19.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==19.0.0.dev0) (3.5.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (2.0.1775222100)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.323.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==19.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.13/site-packages (from inmanta-module-mitogen) (0.3.51)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<50,>=36->inmanta-core==19.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (3.4.9)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper<0.9,>=0.8->inmanta-core==19.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==19.0.0.dev0) (7.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (2.20.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==19.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	f12690c4-509a-4b2e-b555-82bfa2c7ad74
523f8fc3-9b06-4a7e-86f6-63d16662d3bd	2026-07-30 11:24:55.34336+02	2026-07-30 11:24:56.526379+02	/tmp/tmphl8gbyv0/server/a4e5c093-92d5-4ef5-bc72-702dea7e5e1a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a4e5c093-92d5-4ef5-bc72-702dea7e5e1a --server_address localhost --server_port 52757 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpufvaztqa --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:52757/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:52757/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.054 seconds\n	0	f12690c4-509a-4b2e-b555-82bfa2c7ad74
448c83fa-1dda-46aa-b97a-c216be2c9604	2026-07-30 11:24:57.501359+02	2026-07-30 11:24:57.509663+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmphl8gbyv0/server/e30c7032-ae66-4c8b-b004-2973f8943ee6/compiler and no repository set.\n	1	729e5f41-7b45-4a17-a0e7-2fa59f0b651c
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	e7680579-5fde-4cd4-8761-b4d6eb495ceb
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e7680579-5fde-4cd4-8761-b4d6eb495ceb
55d5ed9a-e173-43e6-9221-7fd46544cd1d	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	83df1fb3-56da-475b-8646-e81c3826431c
55d5ed9a-e173-43e6-9221-7fd46544cd1d	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	83df1fb3-56da-475b-8646-e81c3826431c
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	8eeac9e7-75ae-49fa-87fa-cd46f4d0263f
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	8eeac9e7-75ae-49fa-87fa-cd46f4d0263f
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	44b9453a-79cc-4326-90d0-0063e1ac890b
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	44b9453a-79cc-4326-90d0-0063e1ac890b
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	44b9453a-79cc-4326-90d0-0063e1ac890b
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	d9a48882-d012-4372-a232-90d33f13c459
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d9a48882-d012-4372-a232-90d33f13c459
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	48bb687c-d95a-42cb-a9da-72305a823b82
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	48bb687c-d95a-42cb-a9da-72305a823b82
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	ab7ef50f-78e5-4145-9e45-30c0ad1c721e
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ab7ef50f-78e5-4145-9e45-30c0ad1c721e
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	2545ca2d-0efb-4fe5-928c-acc6b83eba38
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	80e915c7-2636-417f-b236-02d1103259dd
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	80e915c7-2636-417f-b236-02d1103259dd
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	bc1af32b-0857-46c1-8073-7d2f40b00123
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	1e303a8e-0da0-4fe6-ad9c-1def61237cfb
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	dd9c030b-829a-4d8b-b7be-b5fc3a548761
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	dd9c030b-829a-4d8b-b7be-b5fc3a548761
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	3c98e24c-f927-4f3c-a88a-f5bda277129a
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	6b829bfe-99e3-41b5-8676-0e97aac4b717
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
e2d1339b-ef4b-4d87-a344-420021d55784	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-07-30 11:24:57.251745+02
976c3940-4c89-4359-8c91-0f3cb2bf721d	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-07-30 11:24:57.256389+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key9]	2026-07-30 11:24:57.262458+02	2026-07-30 11:24:57.259592+02	2026-07-30 11:24:57.262458+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:57.214126+02	t	\N	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key7]	2026-07-30 11:24:57.266104+02	2026-07-30 11:24:57.263201+02	2026-07-30 11:24:57.266104+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:57.214126+02	t	\N	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key3]	2026-07-30 11:24:57.017969+02	\N	2026-07-30 11:24:57.017969+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-07-30 11:24:56.986829+02	f	\N	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key1]	2026-07-30 11:24:57.022151+02	2026-07-30 11:24:57.018804+02	2026-07-30 11:24:57.022151+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:56.986829+02	t	\N	\N
55d5ed9a-e173-43e6-9221-7fd46544cd1d	std::AgentConfig[internal,agentname=localhost]	2026-07-30 11:24:37.53547+02	\N	2026-07-30 11:24:37.53547+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:37.506797+02	f	\N	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	test::Resource[agent3,key=key3]	2026-07-30 11:24:56.594719+02	\N	2026-07-30 11:24:56.594719+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:56.585074+02	f	\N	7
55d5ed9a-e173-43e6-9221-7fd46544cd1d	fs::File[localhost,path=/tmp/test]	2026-07-30 11:24:37.54666+02	\N	2026-07-30 11:24:37.54666+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:37.506797+02	f	\N	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	test::Resource[agent2,key=key2]	2026-07-30 11:24:56.845531+02	\N	2026-07-30 11:24:56.845531+02	509af84c7d978674472e11ce2cad1b8b	8	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:56.585074+02	f	\N	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	std::AgentConfig[internal,agentname=localhost]	2026-07-30 11:24:56.846679+02	\N	2026-07-30 11:24:56.846679+02	b8f697829071c376b6c9e448e5bd267d	8	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:22.838711+02	f	\N	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test]	2026-07-30 11:24:56.849841+02	\N	2026-07-30 11:24:56.849841+02	28b181a98279db3c2d85305e0c4d43c6	8	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:22.838711+02	f	\N	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	fs::File[localhost,path=/tmp/test_orphan]	2026-07-30 11:24:40.44284+02	\N	2026-07-30 11:24:40.44284+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:40.432769+02	f	\N	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-07-30 11:24:56.986829+02	\N	\N	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-07-30 11:24:56.986829+02	\N	\N	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key6]	2026-07-30 11:24:57.012644+02	2026-07-30 11:24:57.002765+02	2026-07-30 11:24:57.012644+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:56.986829+02	t	\N	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key10]	2026-07-30 11:24:57.251745+02	\N	2026-07-30 11:24:57.251745+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:57.214126+02	f	e2d1339b-ef4b-4d87-a344-420021d55784	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Resource[agent1,key=key11]	2026-07-30 11:24:57.256389+02	\N	2026-07-30 11:24:57.256389+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-07-30 11:24:57.214126+02	f	976c3940-4c89-4359-8c91-0f3cb2bf721d	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	test::Fail[agent1,key=key2]	2026-07-30 11:24:57.25884+02	\N	2026-07-30 11:24:57.25884+02	fa7087083326c953261c388f13f3df3c	2	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-07-30 11:24:56.986829+02	f	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	e7680579-5fde-4cd4-8761-b4d6eb495ceb	\N
55d5ed9a-e173-43e6-9221-7fd46544cd1d	83df1fb3-56da-475b-8646-e81c3826431c	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8eeac9e7-75ae-49fa-87fa-cd46f4d0263f	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	44b9453a-79cc-4326-90d0-0063e1ac890b	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	d9a48882-d012-4372-a232-90d33f13c459	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	48bb687c-d95a-42cb-a9da-72305a823b82	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	ab7ef50f-78e5-4145-9e45-30c0ad1c721e	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	80e915c7-2636-417f-b236-02d1103259dd	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	bc1af32b-0857-46c1-8073-7d2f40b00123	set-a
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1e303a8e-0da0-4fe6-ad9c-1def61237cfb	set-b
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	dd9c030b-829a-4d8b-b7be-b5fc3a548761	\N
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3c98e24c-f927-4f3c-a88a-f5bda277129a	set-a
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2545ca2d-0efb-4fe5-928c-acc6b83eba38	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	aa5e0c87-22ed-403c-89f7-f3095328217d	\N
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	6b829bfe-99e3-41b5-8676-0e97aac4b717	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1	e7680579-5fde-4cd4-8761-b4d6eb495ceb
55d5ed9a-e173-43e6-9221-7fd46544cd1d	1	83df1fb3-56da-475b-8646-e81c3826431c
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2	8eeac9e7-75ae-49fa-87fa-cd46f4d0263f
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3	44b9453a-79cc-4326-90d0-0063e1ac890b
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	4	d9a48882-d012-4372-a232-90d33f13c459
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	5	48bb687c-d95a-42cb-a9da-72305a823b82
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	6	ab7ef50f-78e5-4145-9e45-30c0ad1c721e
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	80e915c7-2636-417f-b236-02d1103259dd
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	bc1af32b-0857-46c1-8073-7d2f40b00123
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	1e303a8e-0da0-4fe6-ad9c-1def61237cfb
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	dd9c030b-829a-4d8b-b7be-b5fc3a548761
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	3c98e24c-f927-4f3c-a88a-f5bda277129a
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	2545ca2d-0efb-4fe5-928c-acc6b83eba38
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	aa5e0c87-22ed-403c-89f7-f3095328217d
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3	6b829bfe-99e3-41b5-8676-0e97aac4b717
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
5b6a5103-5e88-497e-9b1f-e450c04f6f2d	store	2026-07-30 11:24:22.403058+02	2026-07-30 11:24:22.409718+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-07-30T11:24:22.409731+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
627d3318-e187-4246-8d77-f3d3f2989a1d	deploy	2026-07-30 11:24:22.846071+02	2026-07-30 11:24:22.848425+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:22.847354+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2592beae-e29b-422b-963e-0880a8995324	deploy	2026-07-30 11:24:22.853645+02	2026-07-30 11:24:22.854894+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:22.854423+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1	{"fs::File[localhost,path=/tmp/test],v=1"}
5c509494-401d-4e89-adf1-34b8c0eb0fdd	store	2026-07-30 11:24:37.084918+02	2026-07-30 11:24:37.090814+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-07-30T11:24:37.090824+02:00\\"}"}	\N	\N	\N	55d5ed9a-e173-43e6-9221-7fd46544cd1d	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
239cca4e-8b9d-48a9-af6c-0ab7da97bea9	deploy	2026-07-30 11:24:37.529648+02	2026-07-30 11:24:37.53547+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:37.533871+02:00\\"}"}	unavailable	\N	nochange	55d5ed9a-e173-43e6-9221-7fd46544cd1d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
8fdb5254-c483-43b4-a205-71a50c723997	deploy	2026-07-30 11:24:37.545535+02	2026-07-30 11:24:37.54666+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:37.546235+02:00\\"}"}	unavailable	\N	nochange	55d5ed9a-e173-43e6-9221-7fd46544cd1d	1	{"fs::File[localhost,path=/tmp/test],v=1"}
8866a8cb-c06c-42b7-a35f-15324f33f48c	store	2026-07-30 11:24:38.626804+02	2026-07-30 11:24:38.628843+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-07-30T11:24:38.628864+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
0bd09b52-df9c-4eb4-820f-bb2155153387	store	2026-07-30 11:24:40.003798+02	2026-07-30 11:24:40.006011+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-07-30T11:24:40.006019+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
3b009f49-1faa-46d5-9d23-d8e742ef1c07	deploy	2026-07-30 11:24:40.435651+02	2026-07-30 11:24:40.437363+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=3: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=3\\"}, \\"timestamp\\": \\"2026-07-30T11:24:40.436870+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
18accad6-0a33-4a77-b812-e6e6dc9627b7	deploy	2026-07-30 11:24:40.439307+02	2026-07-30 11:24:40.440919+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=3\\"}, \\"timestamp\\": \\"2026-07-30T11:24:40.440495+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3	{"fs::File[localhost,path=/tmp/test],v=3"}
8fb357b9-a258-45b1-b54d-33e76d916241	deploy	2026-07-30 11:24:40.441815+02	2026-07-30 11:24:40.44284+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-07-30T11:24:40.442432+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
ec4f8753-fc3c-4fe5-acd9-bc4614a3a398	store	2026-07-30 11:24:41.539052+02	2026-07-30 11:24:41.545311+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-07-30T11:24:41.545320+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	4	{"std::AgentConfig[internal,agentname=localhost],v=4","fs::File[localhost,path=/tmp/test],v=4"}
228a1b07-adc7-4597-9224-02341b0525af	deploy	2026-07-30 11:24:41.859156+02	2026-07-30 11:24:41.861198+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=4: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=4\\"}, \\"timestamp\\": \\"2026-07-30T11:24:41.860678+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	4	{"std::AgentConfig[internal,agentname=localhost],v=4"}
bda20bc2-b18f-4e19-b46d-f50b70e92945	deploy	2026-07-30 11:24:41.86251+02	2026-07-30 11:24:41.863871+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=4: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=4\\"}, \\"timestamp\\": \\"2026-07-30T11:24:41.863440+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	4	{"fs::File[localhost,path=/tmp/test],v=4"}
1d565567-62a9-43ff-92af-92df8949eb57	store	2026-07-30 11:24:42.825123+02	2026-07-30 11:24:42.827177+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-07-30T11:24:42.827186+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
7620be97-b778-4dff-9bed-51662ac5457c	deploy	2026-07-30 11:24:56.591034+02	2026-07-30 11:24:56.593038+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.592377+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	{"test::Resource[agent2,key=key2],v=7"}
ceb2fc21-67e5-4dff-a391-0f2145a2e884	deploy	2026-07-30 11:24:56.593097+02	2026-07-30 11:24:56.594719+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.594173+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	{"test::Resource[agent3,key=key3],v=7"}
7843672b-9752-4780-a4d0-b161850582fe	store	2026-07-30 11:24:56.246381+02	2026-07-30 11:24:56.248464+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-07-30T11:24:56.248472+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	6	{"fs::File[localhost,path=/tmp/test],v=6","std::AgentConfig[internal,agentname=localhost],v=6"}
e4324c6a-71c7-43ab-bc9a-eb9adef78dc5	deploy	2026-07-30 11:24:56.587731+02	2026-07-30 11:24:56.590483+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=7: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=7\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.589963+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	{"std::AgentConfig[internal,agentname=localhost],v=7"}
863420b8-a886-413c-901c-b4d8e3201dc4	deploy	2026-07-30 11:24:56.59661+02	2026-07-30 11:24:56.59779+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=7: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=7\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.597369+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	{"fs::File[localhost,path=/tmp/test],v=7"}
92de033d-ab6f-4566-8f4f-d2535f0b8d68	deploy	2026-07-30 11:24:56.848613+02	2026-07-30 11:24:56.849841+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=8: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=8\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.849443+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	{"fs::File[localhost,path=/tmp/test],v=8"}
3bae2f68-11ca-4e99-9d82-a0076083ec79	store	2026-07-30 11:24:56.968689+02	2026-07-30 11:24:56.976627+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-07-30T11:24:56.976659+02:00\\"}"}	\N	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key3],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key4],v=1"}
8276ec2f-136c-4462-a2ce-94defadc74f8	store	2026-07-30 11:24:56.56011+02	2026-07-30 11:24:56.564164+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-07-30T11:24:56.564172+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7	{"test::Resource[agent2,key=key2],v=7","std::AgentConfig[internal,agentname=localhost],v=7","test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7"}
0cb6f36d-1ae6-4cda-b754-bf0d91fb0e8e	store	2026-07-30 11:24:56.762199+02	2026-07-30 11:24:56.792986+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-07-30T11:24:56.793005+02:00\\"}"}	\N	\N	\N	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8","std::AgentConfig[internal,agentname=localhost],v=8"}
c4823a13-bc3d-4c24-97bf-97c334ccd3dc	deploy	2026-07-30 11:24:56.84394+02	2026-07-30 11:24:56.845531+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=8: Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=8\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.844932+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	{"test::Resource[agent2,key=key2],v=8"}
f33ed671-2bba-4d57-bb71-357bc76a7451	deploy	2026-07-30 11:24:56.845583+02	2026-07-30 11:24:56.846679+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=8: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=8\\"}, \\"timestamp\\": \\"2026-07-30T11:24:56.846283+02:00\\"}"}	unavailable	\N	nochange	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8	{"std::AgentConfig[internal,agentname=localhost],v=8"}
dd7e6eaa-e762-42ce-a595-782c733a27c9	deploy	2026-07-30 11:24:57.002935+02	2026-07-30 11:24:57.012644+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 13540440-e955-4608-923a-b909d6784393).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"13540440-e955-4608-923a-b909d6784393\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.007019+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 13540440-e955-4608-923a-b909d6784393) - duration: 0.0054 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0054438114166259766, \\"deploy_id\\": \\"13540440-e955-4608-923a-b909d6784393\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.012580+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}}}	created	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key6],v=1"}
64a7f5a0-4981-44bd-b936-33488a4cb4a4	deploy	2026-07-30 11:24:57.014178+02	2026-07-30 11:24:57.016145+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: cd9a5134-486e-4420-abff-bd0c8aca6e28).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"cd9a5134-486e-4420-abff-bd0c8aca6e28\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.014952+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2652, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.015631+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: cd9a5134-486e-4420-abff-bd0c8aca6e28) - duration: 0.0011 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0011260509490966797, \\"deploy_id\\": \\"cd9a5134-486e-4420-abff-bd0c8aca6e28\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.016119+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}}}	nochange	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Fail[agent1,key=key2],v=1"}
0dd1dafa-691f-44ef-a698-8ac28479c7fa	store	2026-07-30 11:24:57.359572+02	2026-07-30 11:24:57.361176+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-07-30T11:24:57.361183+02:00\\"}"}	\N	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3	{"test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key7],v=3"}
1ceaa49e-0735-4365-9eca-e653529b2de0	deploy	2026-07-30 11:24:57.017095+02	2026-07-30 11:24:57.017969+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 93e6a3ab-c291-41c8-8a79-1920a82083a3).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"93e6a3ab-c291-41c8-8a79-1920a82083a3\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.017730+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.017870+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 93e6a3ab-c291-41c8-8a79-1920a82083a3) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00018596649169921875, \\"deploy_id\\": \\"93e6a3ab-c291-41c8-8a79-1920a82083a3\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.017949+02:00\\"}"}	skipped	\N	nochange	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key3],v=1"}
c2e889f0-ae87-46c5-9102-148df5f0aecc	deploy	2026-07-30 11:24:57.018828+02	2026-07-30 11:24:57.022151+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: bdcc1999-be43-41dd-9e5e-466a4b6b1ae2).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"bdcc1999-be43-41dd-9e5e-466a4b6b1ae2\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.019400+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: bdcc1999-be43-41dd-9e5e-466a4b6b1ae2) - duration: 0.0027 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.002688169479370117, \\"deploy_id\\": \\"bdcc1999-be43-41dd-9e5e-466a4b6b1ae2\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.022125+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}}}	created	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key1],v=1"}
0d9144c0-7f8f-48b1-9d4b-2c4e3cee257a	dryrun	2026-07-30 11:24:57.150668+02	2026-07-30 11:24:57.151814+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.150859+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007441043853759766, \\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.151763+02:00\\"}"}	dry	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Fail[agent1,key=key2],v=1"}
48e2ae82-910e-4c25-a16e-b5f3ad976c51	dryrun	2026-07-30 11:24:57.168215+02	2026-07-30 11:24:57.16935+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.168375+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518 - duration 0.0008 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007767677307128906, \\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.169301+02:00\\"}"}	dry	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key1],v=1"}
c86d66f1-5e04-4551-9bfc-b353324678e0	dryrun	2026-07-30 11:24:57.181063+02	2026-07-30 11:24:57.18212+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.181223+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007131099700927734, \\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.182080+02:00\\"}"}	dry	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key3],v=1"}
47d04cb6-37ca-48c8-a71e-006bedbd5de2	dryrun	2026-07-30 11:24:57.190159+02	2026-07-30 11:24:57.191058+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.190308+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518 - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005900859832763672, \\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.191017+02:00\\"}"}	dry	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key5],v=1"}
d8354c9b-cec5-4ad2-8d0b-11258d1eac6d	dryrun	2026-07-30 11:24:57.19853+02	2026-07-30 11:24:57.199555+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.198687+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 3ebc47b6-b9f0-4044-acd1-b102967d9518 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006806850433349609, \\"dry_run_id\\": \\"3ebc47b6-b9f0-4044-acd1-b102967d9518\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.199507+02:00\\"}"}	dry	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1	{"test::Resource[agent1,key=key6],v=1"}
b092adcc-3df2-4aec-a625-1e6643a1d7ad	store	2026-07-30 11:24:57.181804+02	2026-07-30 11:24:57.205687+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-07-30T11:24:57.205707+02:00\\"}"}	\N	\N	\N	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key7],v=2","test::Fail[agent1,key=key2],v=2"}
8de60eb0-0388-4e52-b66c-8d3596bb2c52	deploy	2026-07-30 11:24:57.246919+02	2026-07-30 11:24:57.251745+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3e2883dd-2449-410d-8d89-6b50ebcf04d5).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"3e2883dd-2449-410d-8d89-6b50ebcf04d5\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.248519+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.248735+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 3e2883dd-2449-410d-8d89-6b50ebcf04d5) - duration: 0.0031 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0031430721282958984, \\"deploy_id\\": \\"3e2883dd-2449-410d-8d89-6b50ebcf04d5\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.251712+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}}}	nochange	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Resource[agent1,key=key10],v=2"}
d37fe237-d6d6-48f7-b4a4-94a45eb6464a	deploy	2026-07-30 11:24:57.253353+02	2026-07-30 11:24:57.256389+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 47e51682-07a7-49b9-8191-55ecd8d72b48).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"47e51682-07a7-49b9-8191-55ecd8d72b48\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.253963+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.254114+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 47e51682-07a7-49b9-8191-55ecd8d72b48) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.0023555755615234375, \\"deploy_id\\": \\"47e51682-07a7-49b9-8191-55ecd8d72b48\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.256360+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}}}	nochange	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Resource[agent1,key=key11],v=2"}
1aa7c7f9-75df-4b2c-951a-b30803d3cb6c	deploy	2026-07-30 11:24:57.257374+02	2026-07-30 11:24:57.25884+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 11ca0f2f-9a90-46fa-9de3-8f075bf433c9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"11ca0f2f-9a90-46fa-9de3-8f075bf433c9\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.257933+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2652, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.258349+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=2. (deploy_id: 11ca0f2f-9a90-46fa-9de3-8f075bf433c9) - duration: 0.0009 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=2\\", \\"duration\\": 0.0008525848388671875, \\"deploy_id\\": \\"11ca0f2f-9a90-46fa-9de3-8f075bf433c9\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.258820+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=2": {"value": {"current": null, "desired": "val2"}}}	nochange	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Fail[agent1,key=key2],v=2"}
cf93cbcd-c7c8-43fb-9ee4-f1e0b0e84a6d	deploy	2026-07-30 11:24:57.259618+02	2026-07-30 11:24:57.262458+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: fb5cb04b-e401-440e-a8b1-337bdbd8f29a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"fb5cb04b-e401-440e-a8b1-337bdbd8f29a\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.260153+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: fb5cb04b-e401-440e-a8b1-337bdbd8f29a) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.002240896224975586, \\"deploy_id\\": \\"fb5cb04b-e401-440e-a8b1-337bdbd8f29a\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.262432+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}}}	created	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Resource[agent1,key=key9],v=2"}
2fa86891-992b-4d7d-a340-5d79f63992c3	deploy	2026-07-30 11:24:57.263228+02	2026-07-30 11:24:57.266104+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1a008fdc-6116-4881-bbbc-868493f4c515).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"1a008fdc-6116-4881-bbbc-868493f4c515\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.263759+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 1a008fdc-6116-4881-bbbc-868493f4c515) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0022819042205810547, \\"deploy_id\\": \\"1a008fdc-6116-4881-bbbc-868493f4c515\\"}, \\"timestamp\\": \\"2026-07-30T11:24:57.266078+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}}}	created	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2	{"test::Resource[agent1,key=key7],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	5b6a5103-5e88-497e-9b1f-e450c04f6f2d	fs::File[localhost,path=/tmp/test]	1
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	5b6a5103-5e88-497e-9b1f-e450c04f6f2d	std::AgentConfig[internal,agentname=localhost]	1
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	627d3318-e187-4246-8d77-f3d3f2989a1d	std::AgentConfig[internal,agentname=localhost]	1
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2592beae-e29b-422b-963e-0880a8995324	fs::File[localhost,path=/tmp/test]	1
55d5ed9a-e173-43e6-9221-7fd46544cd1d	5c509494-401d-4e89-adf1-34b8c0eb0fdd	fs::File[localhost,path=/tmp/test]	1
55d5ed9a-e173-43e6-9221-7fd46544cd1d	5c509494-401d-4e89-adf1-34b8c0eb0fdd	std::AgentConfig[internal,agentname=localhost]	1
55d5ed9a-e173-43e6-9221-7fd46544cd1d	239cca4e-8b9d-48a9-af6c-0ab7da97bea9	std::AgentConfig[internal,agentname=localhost]	1
55d5ed9a-e173-43e6-9221-7fd46544cd1d	8fdb5254-c483-43b4-a205-71a50c723997	fs::File[localhost,path=/tmp/test]	1
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8866a8cb-c06c-42b7-a35f-15324f33f48c	std::AgentConfig[internal,agentname=localhost]	2
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8866a8cb-c06c-42b7-a35f-15324f33f48c	fs::File[localhost,path=/tmp/test]	2
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0bd09b52-df9c-4eb4-820f-bb2155153387	fs::File[localhost,path=/tmp/test_orphan]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0bd09b52-df9c-4eb4-820f-bb2155153387	fs::File[localhost,path=/tmp/test]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0bd09b52-df9c-4eb4-820f-bb2155153387	std::AgentConfig[internal,agentname=localhost]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	3b009f49-1faa-46d5-9d23-d8e742ef1c07	std::AgentConfig[internal,agentname=localhost]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	18accad6-0a33-4a77-b812-e6e6dc9627b7	fs::File[localhost,path=/tmp/test]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8fb357b9-a258-45b1-b54d-33e76d916241	fs::File[localhost,path=/tmp/test_orphan]	3
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	ec4f8753-fc3c-4fe5-acd9-bc4614a3a398	std::AgentConfig[internal,agentname=localhost]	4
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	ec4f8753-fc3c-4fe5-acd9-bc4614a3a398	fs::File[localhost,path=/tmp/test]	4
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	228a1b07-adc7-4597-9224-02341b0525af	std::AgentConfig[internal,agentname=localhost]	4
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	bda20bc2-b18f-4e19-b46d-f50b70e92945	fs::File[localhost,path=/tmp/test]	4
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1d565567-62a9-43ff-92af-92df8949eb57	std::AgentConfig[internal,agentname=localhost]	5
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	1d565567-62a9-43ff-92af-92df8949eb57	fs::File[localhost,path=/tmp/test]	5
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7843672b-9752-4780-a4d0-b161850582fe	fs::File[localhost,path=/tmp/test]	6
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7843672b-9752-4780-a4d0-b161850582fe	std::AgentConfig[internal,agentname=localhost]	6
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8276ec2f-136c-4462-a2ce-94defadc74f8	test::Resource[agent2,key=key2]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8276ec2f-136c-4462-a2ce-94defadc74f8	std::AgentConfig[internal,agentname=localhost]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8276ec2f-136c-4462-a2ce-94defadc74f8	test::Resource[agent3,key=key3]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8276ec2f-136c-4462-a2ce-94defadc74f8	fs::File[localhost,path=/tmp/test]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	e4324c6a-71c7-43ab-bc9a-eb9adef78dc5	std::AgentConfig[internal,agentname=localhost]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	7620be97-b778-4dff-9bed-51662ac5457c	test::Resource[agent2,key=key2]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	ceb2fc21-67e5-4dff-a391-0f2145a2e884	test::Resource[agent3,key=key3]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	863420b8-a886-413c-901c-b4d8e3201dc4	fs::File[localhost,path=/tmp/test]	7
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0cb6f36d-1ae6-4cda-b754-bf0d91fb0e8e	test::Resource[agent2,key=key2]	8
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0cb6f36d-1ae6-4cda-b754-bf0d91fb0e8e	fs::File[localhost,path=/tmp/test]	8
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	0cb6f36d-1ae6-4cda-b754-bf0d91fb0e8e	std::AgentConfig[internal,agentname=localhost]	8
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	c4823a13-bc3d-4c24-97bf-97c334ccd3dc	test::Resource[agent2,key=key2]	8
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	f33ed671-2bba-4d57-bb71-357bc76a7451	std::AgentConfig[internal,agentname=localhost]	8
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	92de033d-ab6f-4566-8f4f-d2535f0b8d68	fs::File[localhost,path=/tmp/test]	8
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Resource[agent1,key=key5]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Resource[agent1,key=key1]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Resource[agent1,key=key6]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Resource[agent1,key=key3]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Fail[agent1,key=key2]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	3bae2f68-11ca-4e99-9d82-a0076083ec79	test::Resource[agent1,key=key4]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	dd7e6eaa-e762-42ce-a595-782c733a27c9	test::Resource[agent1,key=key6]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	64a7f5a0-4981-44bd-b936-33488a4cb4a4	test::Fail[agent1,key=key2]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1ceaa49e-0735-4365-9eca-e653529b2de0	test::Resource[agent1,key=key3]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	c2e889f0-ae87-46c5-9102-148df5f0aecc	test::Resource[agent1,key=key1]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0d9144c0-7f8f-48b1-9d4b-2c4e3cee257a	test::Fail[agent1,key=key2]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	48e2ae82-910e-4c25-a16e-b5f3ad976c51	test::Resource[agent1,key=key1]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	c86d66f1-5e04-4551-9bfc-b353324678e0	test::Resource[agent1,key=key3]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	47d04cb6-37ca-48c8-a71e-006bedbd5de2	test::Resource[agent1,key=key5]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	d8354c9b-cec5-4ad2-8d0b-11258d1eac6d	test::Resource[agent1,key=key6]	1
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key1]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key4]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key3]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key9]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key10]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key11]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key5]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Resource[agent1,key=key7]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	b092adcc-3df2-4aec-a625-1e6643a1d7ad	test::Fail[agent1,key=key2]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	8de60eb0-0388-4e52-b66c-8d3596bb2c52	test::Resource[agent1,key=key10]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	d37fe237-d6d6-48f7-b4a4-94a45eb6464a	test::Resource[agent1,key=key11]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	1aa7c7f9-75df-4b2c-951a-b30803d3cb6c	test::Fail[agent1,key=key2]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	cf93cbcd-c7c8-43fb-9ee4-f1e0b0e84a6d	test::Resource[agent1,key=key9]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2fa86891-992b-4d7d-a340-5d79f63992c3	test::Resource[agent1,key=key7]	2
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key8]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key5]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Fail[agent1,key=key2]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key4]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key3]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key1]	3
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	0dd1dafa-691f-44ef-a698-8ac28479c7fa	test::Resource[agent1,key=key7]	3
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
55d5ed9a-e173-43e6-9221-7fd46544cd1d	1
a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	8
df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	a4e5c093-92d5-4ef5-bc72-702dea7e5e1a	2026-07-30 11:24:05.751251+02	\N	5df634cf-11d9-4bbe-a97d-bcf931db4168
hugo-Latitude-5421	55d5ed9a-e173-43e6-9221-7fd46544cd1d	2026-07-30 11:24:05.870406+02	\N	f1db92b8-71ba-4222-85ac-4773f42ae61a
hugo-Latitude-5421	df5d779a-d5f5-4c8e-8d42-9b62e7f93e3f	2026-07-30 11:24:56.830622+02	2026-07-30 11:24:57.355247+02	e384da46-e507-408c-9841-38bf889424d6
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

