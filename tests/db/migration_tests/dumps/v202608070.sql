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
    editable_install boolean,
    setup_cfg_hash character varying,
    pyproject_toml_hash character varying
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
863191cf-4ff9-4b06-b8da-b4793d8808c0	$__scheduler	f	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	$__scheduler	f	\N
0a147899-ac4a-466d-b7ab-5466912ab726	$__scheduler	f	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	localhost	f	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	internal	f	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	localhost	f	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	internal	f	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	agent3	f	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	agent2	f	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	agent1	t	t
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	$__scheduler	t	t
ba39b064-0277-4ed6-a360-28e1830a1364	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
1	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
1	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
1	internal	std	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf
1	localhost	fs	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf
2	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
2	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
2	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
3	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
3	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
3	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
4	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
4	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
4	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
5	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
5	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
5	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
6	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
6	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
6	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
7	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
7	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
7	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
8	localhost	fs	863191cf-4ff9-4b06-b8da-b4793d8808c0
8	internal	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
8	localhost	std	863191cf-4ff9-4b06-b8da-b4793d8808c0
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
4c4156fe-f1de-4bb9-8899-38abdbd542a8	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:48:51.06897+02	2026-09-18 15:49:09.406879+02	2026-09-18 15:48:51.060322+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	01c56227-14ab-41b1-b69d-2f29e3f89b29	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
0ee5d152-4ee6-401d-a69d-2951a47c1f04	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	2026-09-18 15:49:09.696072+02	2026-09-18 15:49:24.903688+02	2026-09-18 15:49:09.681487+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	3c86bb04-b7ce-44ab-badb-068f8230f6dd	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
1a1fee68-b4dd-48f5-bee4-717b679db257	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:25.070444+02	2026-09-18 15:49:26.028986+02	2026-09-18 15:49:25.055457+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	6fe6bbb8-29a3-4e99-852a-249f0f4ed24a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a0017656-0493-4429-a22e-78244b4eb45b	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:26.176757+02	2026-09-18 15:49:27.105624+02	2026-09-18 15:49:26.163212+02	{}	{"add_one_resource": "true"}	t	f	t	3	122399da-da06-41ea-83b4-08fb28fa9955	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
52f34f0d-05bd-4d2d-8a17-60c6c46bf077	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:27.271103+02	2026-09-18 15:49:28.254114+02	2026-09-18 15:49:27.254909+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	179754e1-7e2e-4ec4-b660-9e55c82acf1d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a18dc339-56c1-40b8-a9e2-fc27ce5e28a6	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:28.407346+02	2026-09-18 15:49:29.354764+02	2026-09-18 15:49:28.403025+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	a19ea3e6-fa65-451d-85c0-a2992516e384	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
2aa1337c-de39-4320-b827-de820a2e9a74	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:29.535505+02	2026-09-18 15:49:42.45549+02	2026-09-18 15:49:29.523336+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	895a20c2-635b-45a1-8991-ffa3492868ed	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
b4d93038-02ad-4d1c-a11a-0fe4b795282a	ba39b064-0277-4ed6-a360-28e1830a1364	2026-09-18 15:49:43.409896+02	2026-09-18 15:49:43.412648+02	2026-09-18 15:49:43.395202+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	e8046dfa-7250-4491-b347-4262b9a93c91	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:09.388457+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:42.651107+02	t	\N	3	{}	{}	7	t	\N	\N
1	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	2026-09-18 15:49:24.894741+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:26.020632+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:27.09697+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:28.239196+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:29.345809+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:42.445852+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2026-09-18 15:49:42.921548+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:49:42.487824+02	t	\N	4	{}	{}	6	t	\N	\N
2	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2026-09-18 15:49:43.131773+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2026-09-18 15:49:43.274068+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	1	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	1	fs	1.2.0
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	std	7.0.0
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	2	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	2	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	3	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	3	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	4	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	4	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	5	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	5	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	6	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	6	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	7	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	7	std	8.7.4
863191cf-4ff9-4b06-b8da-b4793d8808c0	8	fs	1.2.0
863191cf-4ff9-4b06-b8da-b4793d8808c0	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	discovery::Discovered[myagent,name=discovered]	{}	2026-09-18 15:49:43.277345+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
863191cf-4ff9-4b06-b8da-b4793d8808c0	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-09-18 15:49:43.277365+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
63e6483f-b661-42fc-97e7-3a69c1aa10c8	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	2026-09-18 15:49:43.083629+02	6	0	{"07decda9-f366-5e98-8ba6-1e287c46c9da": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "11361d25-e669-5d65-863c-55058f477c19": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "24942df3-7539-5dab-af7d-edae49161b36": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "28d53cf8-8bbc-58a5-8152-835af59641ad": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "474197cb-8890-57e3-80f9-2ab64fcbdf37": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "859c354f-b482-5d7e-91cd-3f4ad002ce4e": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
ba39b064-0277-4ed6-a360-28e1830a1364	dev-4	9b4572c8-4066-4e8d-b9f5-8718ef839c58			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
863191cf-4ff9-4b06-b8da-b4793d8808c0	dev-1	9b4572c8-4066-4e8d-b9f5-8718ef839c58			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	dev-1-twin	9b4572c8-4066-4e8d-b9f5-8718ef839c58			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
0a147899-ac4a-466d-b7ab-5466912ab726	dev-2	9b4572c8-4066-4e8d-b9f5-8718ef839c58			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	dev-3	9b4572c8-4066-4e8d-b9f5-8718ef839c58			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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

COPY public.inmanta_module (name, version, environment, requirements, editable_install, setup_cfg_hash, pyproject_toml_hash) FROM stdin;
std	8.7.4	863191cf-4ff9-4b06-b8da-b4793d8808c0	\N	f	\N	\N
fs	1.2.0	863191cf-4ff9-4b06-b8da-b4793d8808c0	\N	f	\N	\N
std	7.0.0	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	\N	f	\N	\N
fs	1.2.0	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	\N	f	\N	\N
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
29247394-fc2f-4f7c-b2cf-c18aec183426	ba39b064-0277-4ed6-a360-28e1830a1364	2026-09-18 15:49:43.4145+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/b4d93038-02ad-4d1c-a11a-0fe4b795282a	f	f	b4d93038-02ad-4d1c-a11a-0fe4b795282a
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
9ef83a97-0f91-4a6b-908d-629d0db6156b	fact1	value1	863191cf-4ff9-4b06-b8da-b4793d8808c0	std::testing::NullResource[localhost,name=test1]	fact	2026-09-18 15:49:28.388204+02	{}	f
2e40d8a0-00a6-4246-a3ce-9076bedcb27a	fact2	value2	863191cf-4ff9-4b06-b8da-b4793d8808c0	std::testing::NullResource[localhost,name=test2]	fact	2026-09-18 15:49:28.391818+02	{}	t
5c998076-e521-48dd-8fbf-7e7c3bd64cd7	fact3	value3	863191cf-4ff9-4b06-b8da-b4793d8808c0	std::testing::NullResource[localhost,name=test3]	fact	2026-09-18 15:49:28.39414+02	{}	t
0a23eef3-3ad4-48e9-be57-2b5113e2f84e	parameter1	value1	863191cf-4ff9-4b06-b8da-b4793d8808c0		fact	2026-09-18 15:49:28.396341+02	{}	f
1f44ea1d-e623-4548-af8a-c87e46cd5d5e	parameter2	value2	863191cf-4ff9-4b06-b8da-b4793d8808c0		fact	2026-09-18 15:49:28.398581+02	{}	f
732e5c76-a190-4e86-b935-8efdf46ff283	parameter3	value3	863191cf-4ff9-4b06-b8da-b4793d8808c0		fact	2026-09-18 15:49:28.400756+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
9b4572c8-4066-4e8d-b9f5-8718ef839c58	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
dbcf6776-4021-47e8-be05-e68b139e2874	2026-09-18 15:48:51.069385+02	2026-09-18 15:48:51.07184+02		Init		Using extra environment variables during compile \n	0	4c4156fe-f1de-4bb9-8899-38abdbd542a8
107cb4f6-de2b-4789-80f1-c057b9edc5ce	2026-09-18 15:48:51.072117+02	2026-09-18 15:48:51.083021+02		Venv check		Creating new venv at /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env-py3.14\n	0	4c4156fe-f1de-4bb9-8899-38abdbd542a8
fe8e540e-585e-4698-af8f-3ccf00ac3d2d	2026-09-18 15:48:51.084684+02	2026-09-18 15:48:51.441353+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	4c4156fe-f1de-4bb9-8899-38abdbd542a8
1fa55856-788d-4be7-8bee-143346601058	2026-09-18 15:48:51.442166+02	2026-09-18 15:49:08.434328+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp6_l_w9dl:\n                                 Pip command: /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp6_l_w9dl inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading pyjwt-2.14.0-py3-none-any.whl (32 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading tornado-6.5.10-cp39-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (467 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading sqlalchemy-2.0.54-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (3.4 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.4/3.4 MB 15.1 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from SQLAlchemy~=2.0->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.4)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, SQLAlchemy, PyJWT, mitogen, build, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.8\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.0.52\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.13.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed PyJWT-2.14.0 SQLAlchemy-2.0.54 build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53 tornado-6.5.10\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	4c4156fe-f1de-4bb9-8899-38abdbd542a8
c7cb7ada-407c-4769-8345-8422bca040a1	2026-09-18 15:49:08.435085+02	2026-09-18 15:49:09.406386+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3ie1iood --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.020 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.014 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.023 seconds\ncompiler       DEBUG   The entire export command took 0.083 seconds\n	0	4c4156fe-f1de-4bb9-8899-38abdbd542a8
9f80ecd7-3a13-4056-b750-6bcf54de9edc	2026-09-18 15:49:09.696615+02	2026-09-18 15:49:09.698908+02		Init		Using extra environment variables during compile \n	0	0ee5d152-4ee6-401d-a69d-2951a47c1f04
eb4d3cca-e099-41e0-8116-e0129f777c32	2026-09-18 15:49:25.073428+02	2026-09-18 15:49:25.080925+02		Init		Using extra environment variables during compile \n	0	1a1fee68-b4dd-48f5-bee4-717b679db257
6ba862ac-bed5-4245-8ca7-daaa8e77fe40	2026-09-18 15:49:09.699226+02	2026-09-18 15:49:09.711735+02		Venv check		Creating new venv at /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env-py3.14\n	0	0ee5d152-4ee6-401d-a69d-2951a47c1f04
5a4a631b-a859-4445-b952-d2eb047f1215	2026-09-18 15:49:25.082087+02	2026-09-18 15:49:25.084396+02		Venv check		Found existing venv\n	0	1a1fee68-b4dd-48f5-bee4-717b679db257
9494e7dc-4576-4d3f-aab6-a5bde9a1526f	2026-09-18 15:49:09.713598+02	2026-09-18 15:49:10.015303+02	/tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	0ee5d152-4ee6-401d-a69d-2951a47c1f04
1f3e2b9d-1b77-47a5-a402-2886bdc0cb4f	2026-09-18 15:49:26.179539+02	2026-09-18 15:49:26.187438+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	a0017656-0493-4429-a22e-78244b4eb45b
282a14e4-2d1c-4554-a6a0-44a7fda18504	2026-09-18 15:49:10.015912+02	2026-09-18 15:49:24.00323+02	/tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpclql00s8:\n                                 Pip command: /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpclql00s8 inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pyjwt-2.14.0-py3-none-any.whl (32 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.5.10-cp39-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (467 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.0.54-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (3.4 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from SQLAlchemy~=2.0->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.4)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, SQLAlchemy, PyJWT, mitogen, build, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.8\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.0.52\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.13.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed PyJWT-2.14.0 SQLAlchemy-2.0.54 build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53 tornado-6.5.10\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	0ee5d152-4ee6-401d-a69d-2951a47c1f04
0aec28d5-ddf0-4fcf-a762-3d4376091dbf	2026-09-18 15:49:26.187906+02	2026-09-18 15:49:26.188348+02		Venv check		Found existing venv\n	0	a0017656-0493-4429-a22e-78244b4eb45b
96e0a988-4b71-41c9-ba12-bf4613ccffcc	2026-09-18 15:49:24.00404+02	2026-09-18 15:49:24.903266+02	/tmp/tmpy1um63nj/server/a2df72fc-4641-4e20-8e6d-28ce22a6f2bf/compiler/.env/bin/python -m inmanta.app -vvv export -X -e a2df72fc-4641-4e20-8e6d-28ce22a6f2bf --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfuuhurvb --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.048 seconds\n	0	0ee5d152-4ee6-401d-a69d-2951a47c1f04
53ca0543-45ac-4e74-a87b-84ba9e0722a2	2026-09-18 15:49:28.407779+02	2026-09-18 15:49:28.40989+02		Init		Using extra environment variables during compile \n	0	a18dc339-56c1-40b8-a9e2-fc27ce5e28a6
123ab200-d336-4e6b-9492-5b46ae6d954a	2026-09-18 15:49:28.410162+02	2026-09-18 15:49:28.410714+02		Venv check		Found existing venv\n	0	a18dc339-56c1-40b8-a9e2-fc27ce5e28a6
5e5142df-4606-4838-af00-62f715cd4a6e	2026-09-18 15:49:25.08533+02	2026-09-18 15:49:26.028495+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfdpxlwan --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.049 seconds\n	0	1a1fee68-b4dd-48f5-bee4-717b679db257
2be7ce97-bba9-458e-bf06-eddc91bc8e36	2026-09-18 15:49:27.272507+02	2026-09-18 15:49:27.279821+02		Init		Using extra environment variables during compile \n	0	52f34f0d-05bd-4d2d-8a17-60c6c46bf077
94053ec4-4658-4d7b-a1a7-8f0e5599a007	2026-09-18 15:49:27.280819+02	2026-09-18 15:49:27.282858+02		Venv check		Found existing venv\n	0	52f34f0d-05bd-4d2d-8a17-60c6c46bf077
46dbf9e3-ecd2-4b97-82a9-36ff20b390ca	2026-09-18 15:49:26.188537+02	2026-09-18 15:49:27.105211+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpkn_v45at --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	a0017656-0493-4429-a22e-78244b4eb45b
89a7bc0d-f186-470b-b8c2-39b36c427290	2026-09-18 15:49:43.411053+02	2026-09-18 15:49:43.412358+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpy1um63nj/server/ba39b064-0277-4ed6-a360-28e1830a1364/compiler and no repository set.\n	1	b4d93038-02ad-4d1c-a11a-0fe4b795282a
294b0925-4bfc-4cec-816b-31c5c05085c9	2026-09-18 15:49:29.550743+02	2026-09-18 15:49:29.916433+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	2aa1337c-de39-4320-b827-de820a2e9a74
d02d4974-d156-461e-9927-ddc86a834ccc	2026-09-18 15:49:27.283789+02	2026-09-18 15:49:28.253672+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcj8jdxd3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.058 seconds\n	0	52f34f0d-05bd-4d2d-8a17-60c6c46bf077
0f3c80a2-85b3-4a44-b666-9c5cdbb00c90	2026-09-18 15:49:29.538914+02	2026-09-18 15:49:29.544691+02		Init		Using extra environment variables during compile \n	0	2aa1337c-de39-4320-b827-de820a2e9a74
3aebadaa-da90-4b62-be3a-ca48dc0d714c	2026-09-18 15:49:29.545532+02	2026-09-18 15:49:29.547095+02		Venv check		Found existing venv\n	0	2aa1337c-de39-4320-b827-de820a2e9a74
ff6fef79-defd-4ad1-abd7-726455f72797	2026-09-18 15:49:28.410963+02	2026-09-18 15:49:29.354376+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpf1uk_7bf --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	a18dc339-56c1-40b8-a9e2-fc27ce5e28a6
b6c49cf2-9e9f-44e3-90b6-9f340cb55e73	2026-09-18 15:49:29.917102+02	2026-09-18 15:49:41.560899+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp5jmelu_2:\n                                 Pip command: /tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp5jmelu_2 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.14.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.0.54)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from SQLAlchemy~=2.0->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.4)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	2aa1337c-de39-4320-b827-de820a2e9a74
49d63d87-4845-4df3-8bc7-00d5bb1b8cd3	2026-09-18 15:49:41.561667+02	2026-09-18 15:49:42.455067+02	/tmp/tmpy1um63nj/server/863191cf-4ff9-4b06-b8da-b4793d8808c0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 863191cf-4ff9-4b06-b8da-b4793d8808c0 --server_address localhost --server_port 38357 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpqkfgle4t --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:38357/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:38357/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	2aa1337c-de39-4320-b827-de820a2e9a74
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	bf9c4988-ee5a-4693-8cff-224f346c5c9a
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	bf9c4988-ee5a-4693-8cff-224f346c5c9a
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	10cc1ea9-6efe-43cf-9a69-c140db174147
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	10cc1ea9-6efe-43cf-9a69-c140db174147
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	042c3bf0-3a3d-4563-9f96-f5828795e874
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	042c3bf0-3a3d-4563-9f96-f5828795e874
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	580156e9-982e-4de2-87d1-330b19d313b0
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	580156e9-982e-4de2-87d1-330b19d313b0
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	580156e9-982e-4de2-87d1-330b19d313b0
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	eae0e65a-2d7d-4f3d-8c67-49557819142d
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	eae0e65a-2d7d-4f3d-8c67-49557819142d
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	6530d709-b079-49ce-bcfe-aee0ca48f314
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6530d709-b079-49ce-bcfe-aee0ca48f314
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	cf147e46-1b1f-4d29-be30-d07485c7d039
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	cf147e46-1b1f-4d29-be30-d07485c7d039
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	78d2a4d5-bf5f-4b1c-b842-095f9baad87d
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	78d2a4d5-bf5f-4b1c-b842-095f9baad87d
863191cf-4ff9-4b06-b8da-b4793d8808c0	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	2ef2de95-6362-4970-a6de-ec4df4ae30c2
863191cf-4ff9-4b06-b8da-b4793d8808c0	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	454f9095-2352-4232-a01e-f754e6a5234b
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	4447951a-2564-40ee-8b03-f68aee00c115
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	4447951a-2564-40ee-8b03-f68aee00c115
863191cf-4ff9-4b06-b8da-b4793d8808c0	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	15544b2b-4c99-4396-90c1-b3513bd445aa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	e0020d24-f4f8-4362-9e57-8d427e1c8baa
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
10058114-aad1-482d-a8f7-56fce7ef9808	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-09-18 15:49:43.224346+02
dbe3a292-819b-4033-9b9e-e05033f8b70e	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-09-18 15:49:43.23051+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key11]	2026-09-18 15:49:43.224346+02	\N	2026-09-18 15:49:43.224346+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:43.157609+02	f	10058114-aad1-482d-a8f7-56fce7ef9808	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-09-18 15:49:42.938356+02	\N	\N	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	std::AgentConfig[internal,agentname=localhost]	2026-09-18 15:49:09.545965+02	\N	2026-09-18 15:49:09.545965+02	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:09.529116+02	f	\N	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-09-18 15:49:42.938356+02	\N	\N	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test]	2026-09-18 15:49:09.550879+02	\N	2026-09-18 15:49:09.550879+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:09.529116+02	f	\N	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key10]	2026-09-18 15:49:43.23051+02	\N	2026-09-18 15:49:43.23051+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:43.157609+02	f	dbe3a292-819b-4033-9b9e-e05033f8b70e	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key7]	2026-09-18 15:49:43.234324+02	2026-09-18 15:49:43.231445+02	2026-09-18 15:49:43.234324+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:43.157609+02	t	\N	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	std::AgentConfig[internal,agentname=localhost]	2026-09-18 15:49:24.933444+02	\N	2026-09-18 15:49:24.933444+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:24.92332+02	f	\N	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	fs::File[localhost,path=/tmp/test]	2026-09-18 15:49:24.938938+02	\N	2026-09-18 15:49:24.938938+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:24.92332+02	f	\N	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key1]	2026-09-18 15:49:42.965509+02	2026-09-18 15:49:42.961972+02	2026-09-18 15:49:42.965509+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:42.938356+02	t	\N	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key9]	2026-09-18 15:49:43.238007+02	2026-09-18 15:49:43.235031+02	2026-09-18 15:49:43.238007+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:43.157609+02	t	\N	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Fail[agent1,key=key2]	2026-09-18 15:49:42.968116+02	\N	2026-09-18 15:49:42.968116+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:42.938356+02	f	\N	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	fs::File[localhost,path=/tmp/test_orphan]	2026-09-18 15:49:27.134818+02	\N	2026-09-18 15:49:27.134818+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:27.127214+02	f	\N	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key3]	2026-09-18 15:49:42.969844+02	\N	2026-09-18 15:49:42.969844+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-09-18 15:49:42.938356+02	f	\N	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	test::Resource[agent2,key=key2]	2026-09-18 15:49:42.526566+02	\N	2026-09-18 15:49:42.526566+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:42.517815+02	f	\N	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	test::Resource[agent3,key=key3]	2026-09-18 15:49:42.52498+02	\N	2026-09-18 15:49:42.52498+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-09-18 15:49:42.517815+02	f	\N	7
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	test::Resource[agent1,key=key6]	2026-09-18 15:49:42.960454+02	2026-09-18 15:49:42.944484+02	2026-09-18 15:49:42.960454+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-18 15:49:42.938356+02	t	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	bf9c4988-ee5a-4693-8cff-224f346c5c9a	\N
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	10cc1ea9-6efe-43cf-9a69-c140db174147	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	042c3bf0-3a3d-4563-9f96-f5828795e874	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	580156e9-982e-4de2-87d1-330b19d313b0	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	eae0e65a-2d7d-4f3d-8c67-49557819142d	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	6530d709-b079-49ce-bcfe-aee0ca48f314	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	cf147e46-1b1f-4d29-be30-d07485c7d039	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	78d2a4d5-bf5f-4b1c-b842-095f9baad87d	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	2ef2de95-6362-4970-a6de-ec4df4ae30c2	set-b
863191cf-4ff9-4b06-b8da-b4793d8808c0	454f9095-2352-4232-a01e-f754e6a5234b	set-a
863191cf-4ff9-4b06-b8da-b4793d8808c0	4447951a-2564-40ee-8b03-f68aee00c115	\N
863191cf-4ff9-4b06-b8da-b4793d8808c0	15544b2b-4c99-4396-90c1-b3513bd445aa	set-a
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	d05748aa-e142-4899-a882-4755d1e3ec43	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	869883e1-ef5e-41ab-9ea2-b0ade37aeb29	\N
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	e0020d24-f4f8-4362-9e57-8d427e1c8baa	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	1	bf9c4988-ee5a-4693-8cff-224f346c5c9a
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	10cc1ea9-6efe-43cf-9a69-c140db174147
863191cf-4ff9-4b06-b8da-b4793d8808c0	2	042c3bf0-3a3d-4563-9f96-f5828795e874
863191cf-4ff9-4b06-b8da-b4793d8808c0	3	580156e9-982e-4de2-87d1-330b19d313b0
863191cf-4ff9-4b06-b8da-b4793d8808c0	4	eae0e65a-2d7d-4f3d-8c67-49557819142d
863191cf-4ff9-4b06-b8da-b4793d8808c0	5	6530d709-b079-49ce-bcfe-aee0ca48f314
863191cf-4ff9-4b06-b8da-b4793d8808c0	6	cf147e46-1b1f-4d29-be30-d07485c7d039
863191cf-4ff9-4b06-b8da-b4793d8808c0	7	78d2a4d5-bf5f-4b1c-b842-095f9baad87d
863191cf-4ff9-4b06-b8da-b4793d8808c0	7	2ef2de95-6362-4970-a6de-ec4df4ae30c2
863191cf-4ff9-4b06-b8da-b4793d8808c0	7	454f9095-2352-4232-a01e-f754e6a5234b
863191cf-4ff9-4b06-b8da-b4793d8808c0	8	4447951a-2564-40ee-8b03-f68aee00c115
863191cf-4ff9-4b06-b8da-b4793d8808c0	8	15544b2b-4c99-4396-90c1-b3513bd445aa
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	d05748aa-e142-4899-a882-4755d1e3ec43
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	869883e1-ef5e-41ab-9ea2-b0ade37aeb29
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	3	e0020d24-f4f8-4362-9e57-8d427e1c8baa
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
1a77faf6-fbd4-4337-ad64-5a9f12f948d2	store	2026-09-18 15:49:09.388403+02	2026-09-18 15:49:09.395211+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-18T15:49:09.395224+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
b407d480-0413-4e9c-b6fc-6f68e6512e85	deploy	2026-09-18 15:49:09.537421+02	2026-09-18 15:49:09.545965+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:09.545232+02:00\\"}"}	unavailable	\N	nochange	863191cf-4ff9-4b06-b8da-b4793d8808c0	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
7a1619a4-e3e5-4b23-9aec-5c2799862766	deploy	2026-09-18 15:49:09.549731+02	2026-09-18 15:49:09.550879+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:09.550453+02:00\\"}"}	unavailable	\N	nochange	863191cf-4ff9-4b06-b8da-b4793d8808c0	1	{"fs::File[localhost,path=/tmp/test],v=1"}
3d07ea4d-59a9-4a6b-b820-13080487cf41	store	2026-09-18 15:49:24.89469+02	2026-09-18 15:49:24.897051+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-18T15:49:24.897061+02:00\\"}"}	\N	\N	\N	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
6eb15174-eafb-4657-99d3-6cbf58b6528c	deploy	2026-09-18 15:49:24.931164+02	2026-09-18 15:49:24.933444+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:24.932915+02:00\\"}"}	unavailable	\N	nochange	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5a6b9579-73b5-4c03-9819-e9f7b8ac0132	deploy	2026-09-18 15:49:24.937834+02	2026-09-18 15:49:24.938938+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:24.938524+02:00\\"}"}	unavailable	\N	nochange	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1	{"fs::File[localhost,path=/tmp/test],v=1"}
d86ed419-6f58-4f05-92fa-8eb0c6971612	store	2026-09-18 15:49:26.020583+02	2026-09-18 15:49:26.022706+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-18T15:49:26.022714+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
b0c70e6a-ba03-4bc0-aeba-638f482ecc8c	store	2026-09-18 15:49:27.096913+02	2026-09-18 15:49:27.099172+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-18T15:49:27.099183+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
66438b70-395e-4ec2-ba19-d68934220b09	deploy	2026-09-18 15:49:27.13065+02	2026-09-18 15:49:27.134818+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-09-18T15:49:27.134333+02:00\\"}"}	unavailable	\N	nochange	863191cf-4ff9-4b06-b8da-b4793d8808c0	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
0d32e39b-8c9f-4828-b82b-7daf160a8898	store	2026-09-18 15:49:28.239147+02	2026-09-18 15:49:28.244884+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-09-18T15:49:28.244893+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	4	{"std::AgentConfig[internal,agentname=localhost],v=4","fs::File[localhost,path=/tmp/test],v=4"}
cbea9e2b-1dd2-4b53-a413-9bbd6521a3ea	store	2026-09-18 15:49:29.345759+02	2026-09-18 15:49:29.348104+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-09-18T15:49:29.348113+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
4cb70743-29f0-4aa4-b48c-136660076225	store	2026-09-18 15:49:42.445806+02	2026-09-18 15:49:42.447939+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-09-18T15:49:42.447948+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	6	{"std::AgentConfig[internal,agentname=localhost],v=6","fs::File[localhost,path=/tmp/test],v=6"}
934a66ac-29b6-4057-9d15-da8f7b532447	store	2026-09-18 15:49:42.487719+02	2026-09-18 15:49:42.496146+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-09-18T15:49:42.496154+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	7	{"test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7","std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7"}
719cf514-90cf-45ce-80a8-4d86af556b07	deploy	2026-09-18 15:49:42.522954+02	2026-09-18 15:49:42.52498+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.524422+02:00\\"}"}	unavailable	\N	nochange	863191cf-4ff9-4b06-b8da-b4793d8808c0	7	{"test::Resource[agent3,key=key3],v=7"}
4a42f555-e26b-4bb1-83b0-0af8e78243f8	deploy	2026-09-18 15:49:42.525038+02	2026-09-18 15:49:42.526566+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.526003+02:00\\"}"}	unavailable	\N	nochange	863191cf-4ff9-4b06-b8da-b4793d8808c0	7	{"test::Resource[agent2,key=key2],v=7"}
5afae45d-42bf-46ff-a39b-41e43eb20a0f	store	2026-09-18 15:49:42.650681+02	2026-09-18 15:49:42.672067+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-09-18T15:49:42.672099+02:00\\"}"}	\N	\N	\N	863191cf-4ff9-4b06-b8da-b4793d8808c0	8	{"test::Resource[agent2,key=key2],v=8","std::AgentConfig[internal,agentname=localhost],v=8","fs::File[localhost,path=/tmp/test],v=8"}
0d035e48-95b7-4024-8e5f-e252a205fc47	store	2026-09-18 15:49:42.92131+02	2026-09-18 15:49:42.929221+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-18T15:49:42.929252+02:00\\"}"}	\N	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key3],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1"}
c82c46cb-6119-4072-9536-489a6d41bf43	deploy	2026-09-18 15:49:42.944529+02	2026-09-18 15:49:42.960454+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2a1b20ed-b585-4438-b74b-2194d54f4c7e).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"2a1b20ed-b585-4438-b74b-2194d54f4c7e\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.952922+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 2a1b20ed-b585-4438-b74b-2194d54f4c7e) - duration: 0.0073 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.007273674011230469, \\"deploy_id\\": \\"2a1b20ed-b585-4438-b74b-2194d54f4c7e\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.960333+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key6],v=1"}
63cf9e5d-9770-4b9f-adbb-9054902ca9dc	deploy	2026-09-18 15:49:42.962006+02	2026-09-18 15:49:42.965509+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 36cb3ae7-a354-4eac-adab-5dde49f9f1ed).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"36cb3ae7-a354-4eac-adab-5dde49f9f1ed\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.962757+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 36cb3ae7-a354-4eac-adab-5dde49f9f1ed) - duration: 0.0027 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0026772022247314453, \\"deploy_id\\": \\"36cb3ae7-a354-4eac-adab-5dde49f9f1ed\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.965478+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key1],v=1"}
5040217a-04f4-48aa-a44b-7905f2cd6f63	deploy	2026-09-18 15:49:42.966318+02	2026-09-18 15:49:42.968116+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: fccac61e-7fcf-4d0d-8ed5-c31a296bc961).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"fccac61e-7fcf-4d0d-8ed5-c31a296bc961\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.966961+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2644, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.967581+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: fccac61e-7fcf-4d0d-8ed5-c31a296bc961) - duration: 0.0011 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0010957717895507812, \\"deploy_id\\": \\"fccac61e-7fcf-4d0d-8ed5-c31a296bc961\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.968092+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Fail[agent1,key=key2],v=1"}
a5b300ef-d2c5-49c4-85d8-eceee52e8a0f	deploy	2026-09-18 15:49:42.968973+02	2026-09-18 15:49:42.969844+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f2564b2f-b1a2-4eb5-8444-ba50f6e88d69).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"f2564b2f-b1a2-4eb5-8444-ba50f6e88d69\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.969618+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.969745+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: f2564b2f-b1a2-4eb5-8444-ba50f6e88d69) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00017118453979492188, \\"deploy_id\\": \\"f2564b2f-b1a2-4eb5-8444-ba50f6e88d69\\"}, \\"timestamp\\": \\"2026-09-18T15:49:42.969822+02:00\\"}"}	skipped	\N	nochange	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key3],v=1"}
9da5d094-de9d-4bc8-a294-0a3aea17ab7a	dryrun	2026-09-18 15:49:43.097018+02	2026-09-18 15:49:43.098504+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.097278+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8 - duration 0.0010 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0009751319885253906, \\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.098439+02:00\\"}"}	dry	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Fail[agent1,key=key2],v=1"}
75ce0fb9-afd7-47d4-a56c-f006dca12975	store	2026-09-18 15:49:43.131268+02	2026-09-18 15:49:43.153904+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-18T15:49:43.153920+02:00\\"}"}	\N	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	{"test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key7],v=2"}
3c31882f-c2d1-4104-8407-a4aad1a465ad	deploy	2026-09-18 15:49:43.206407+02	2026-09-18 15:49:43.224346+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 8632cac3-a217-4d0b-af71-7ffc5db15044).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"8632cac3-a217-4d0b-af71-7ffc5db15044\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.213589+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.214264+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 8632cac3-a217-4d0b-af71-7ffc5db15044) - duration: 0.0104 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.010425567626953125, \\"deploy_id\\": \\"8632cac3-a217-4d0b-af71-7ffc5db15044\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.224215+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	{"test::Resource[agent1,key=key11],v=2"}
1de7fe4d-1695-4f61-9a1c-d149ee38e785	deploy	2026-09-18 15:49:43.227477+02	2026-09-18 15:49:43.23051+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 983c523d-314b-4d6c-9d18-c35dade86ed7).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"983c523d-314b-4d6c-9d18-c35dade86ed7\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.228060+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.228231+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 983c523d-314b-4d6c-9d18-c35dade86ed7) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.002379179000854492, \\"deploy_id\\": \\"983c523d-314b-4d6c-9d18-c35dade86ed7\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.230480+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	{"test::Resource[agent1,key=key10],v=2"}
ca0b0e10-a9db-45ee-a87f-39f2d4743836	deploy	2026-09-18 15:49:43.231473+02	2026-09-18 15:49:43.234324+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2bfe60bc-f158-46e8-952d-67ebd6cdce56).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"2bfe60bc-f158-46e8-952d-67ebd6cdce56\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.232010+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 2bfe60bc-f158-46e8-952d-67ebd6cdce56) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0022449493408203125, \\"deploy_id\\": \\"2bfe60bc-f158-46e8-952d-67ebd6cdce56\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.234295+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	{"test::Resource[agent1,key=key7],v=2"}
0f14abab-2af7-43cd-a93b-4b2ff21d7a79	deploy	2026-09-18 15:49:43.235056+02	2026-09-18 15:49:43.238007+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: b112ba53-2568-4ed2-8b6f-c32843f5d568).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"b112ba53-2568-4ed2-8b6f-c32843f5d568\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.235601+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: b112ba53-2568-4ed2-8b6f-c32843f5d568) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0023381710052490234, \\"deploy_id\\": \\"b112ba53-2568-4ed2-8b6f-c32843f5d568\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.237980+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2	{"test::Resource[agent1,key=key9],v=2"}
ce53aba8-971e-4a41-8a1d-14209c860635	dryrun	2026-09-18 15:49:43.118793+02	2026-09-18 15:49:43.120417+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.118962+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8 - duration 0.0012 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0012493133544921875, \\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.120362+02:00\\"}"}	dry	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key1],v=1"}
dc5f2a6f-87af-4daa-8a60-ca46aa650209	dryrun	2026-09-18 15:49:43.134309+02	2026-09-18 15:49:43.135591+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.134538+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8 - duration 0.0008 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007834434509277344, \\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.135522+02:00\\"}"}	dry	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key3],v=1"}
73db2e99-cc65-46e0-84af-b3ee4b3e67ce	dryrun	2026-09-18 15:49:43.1439+02	2026-09-18 15:49:43.144798+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.144074+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005421638488769531, \\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.144755+02:00\\"}"}	dry	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key5],v=1"}
ae5ee851-6329-4d2f-800f-a710cdd1b549	dryrun	2026-09-18 15:49:43.150977+02	2026-09-18 15:49:43.151636+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.151072+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 63e6483f-b661-42fc-97e7-3a69c1aa10c8 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00043463706970214844, \\"dry_run_id\\": \\"63e6483f-b661-42fc-97e7-3a69c1aa10c8\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-18T15:49:43.151602+02:00\\"}"}	dry	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1	{"test::Resource[agent1,key=key6],v=1"}
51198b43-7314-4d50-a0e9-9ae4a91703d0	store	2026-09-18 15:49:43.274025+02	2026-09-18 15:49:43.275562+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-18T15:49:43.275568+02:00\\"}"}	\N	\N	\N	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	3	{"test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key1],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
863191cf-4ff9-4b06-b8da-b4793d8808c0	1a77faf6-fbd4-4337-ad64-5a9f12f948d2	fs::File[localhost,path=/tmp/test]	1
863191cf-4ff9-4b06-b8da-b4793d8808c0	1a77faf6-fbd4-4337-ad64-5a9f12f948d2	std::AgentConfig[internal,agentname=localhost]	1
863191cf-4ff9-4b06-b8da-b4793d8808c0	b407d480-0413-4e9c-b6fc-6f68e6512e85	std::AgentConfig[internal,agentname=localhost]	1
863191cf-4ff9-4b06-b8da-b4793d8808c0	7a1619a4-e3e5-4b23-9aec-5c2799862766	fs::File[localhost,path=/tmp/test]	1
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	3d07ea4d-59a9-4a6b-b820-13080487cf41	fs::File[localhost,path=/tmp/test]	1
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	3d07ea4d-59a9-4a6b-b820-13080487cf41	std::AgentConfig[internal,agentname=localhost]	1
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	6eb15174-eafb-4657-99d3-6cbf58b6528c	std::AgentConfig[internal,agentname=localhost]	1
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	5a6b9579-73b5-4c03-9819-e9f7b8ac0132	fs::File[localhost,path=/tmp/test]	1
863191cf-4ff9-4b06-b8da-b4793d8808c0	d86ed419-6f58-4f05-92fa-8eb0c6971612	std::AgentConfig[internal,agentname=localhost]	2
863191cf-4ff9-4b06-b8da-b4793d8808c0	d86ed419-6f58-4f05-92fa-8eb0c6971612	fs::File[localhost,path=/tmp/test]	2
863191cf-4ff9-4b06-b8da-b4793d8808c0	b0c70e6a-ba03-4bc0-aeba-638f482ecc8c	fs::File[localhost,path=/tmp/test_orphan]	3
863191cf-4ff9-4b06-b8da-b4793d8808c0	b0c70e6a-ba03-4bc0-aeba-638f482ecc8c	fs::File[localhost,path=/tmp/test]	3
863191cf-4ff9-4b06-b8da-b4793d8808c0	b0c70e6a-ba03-4bc0-aeba-638f482ecc8c	std::AgentConfig[internal,agentname=localhost]	3
863191cf-4ff9-4b06-b8da-b4793d8808c0	66438b70-395e-4ec2-ba19-d68934220b09	fs::File[localhost,path=/tmp/test_orphan]	3
863191cf-4ff9-4b06-b8da-b4793d8808c0	0d32e39b-8c9f-4828-b82b-7daf160a8898	std::AgentConfig[internal,agentname=localhost]	4
863191cf-4ff9-4b06-b8da-b4793d8808c0	0d32e39b-8c9f-4828-b82b-7daf160a8898	fs::File[localhost,path=/tmp/test]	4
863191cf-4ff9-4b06-b8da-b4793d8808c0	cbea9e2b-1dd2-4b53-a413-9bbd6521a3ea	std::AgentConfig[internal,agentname=localhost]	5
863191cf-4ff9-4b06-b8da-b4793d8808c0	cbea9e2b-1dd2-4b53-a413-9bbd6521a3ea	fs::File[localhost,path=/tmp/test]	5
863191cf-4ff9-4b06-b8da-b4793d8808c0	4cb70743-29f0-4aa4-b48c-136660076225	std::AgentConfig[internal,agentname=localhost]	6
863191cf-4ff9-4b06-b8da-b4793d8808c0	4cb70743-29f0-4aa4-b48c-136660076225	fs::File[localhost,path=/tmp/test]	6
863191cf-4ff9-4b06-b8da-b4793d8808c0	934a66ac-29b6-4057-9d15-da8f7b532447	test::Resource[agent2,key=key2]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	934a66ac-29b6-4057-9d15-da8f7b532447	test::Resource[agent3,key=key3]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	934a66ac-29b6-4057-9d15-da8f7b532447	std::AgentConfig[internal,agentname=localhost]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	934a66ac-29b6-4057-9d15-da8f7b532447	fs::File[localhost,path=/tmp/test]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	719cf514-90cf-45ce-80a8-4d86af556b07	test::Resource[agent3,key=key3]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	4a42f555-e26b-4bb1-83b0-0af8e78243f8	test::Resource[agent2,key=key2]	7
863191cf-4ff9-4b06-b8da-b4793d8808c0	5afae45d-42bf-46ff-a39b-41e43eb20a0f	test::Resource[agent2,key=key2]	8
863191cf-4ff9-4b06-b8da-b4793d8808c0	5afae45d-42bf-46ff-a39b-41e43eb20a0f	std::AgentConfig[internal,agentname=localhost]	8
863191cf-4ff9-4b06-b8da-b4793d8808c0	5afae45d-42bf-46ff-a39b-41e43eb20a0f	fs::File[localhost,path=/tmp/test]	8
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Resource[agent1,key=key1]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Resource[agent1,key=key3]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Fail[agent1,key=key2]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Resource[agent1,key=key4]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Resource[agent1,key=key6]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0d035e48-95b7-4024-8e5f-e252a205fc47	test::Resource[agent1,key=key5]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	c82c46cb-6119-4072-9536-489a6d41bf43	test::Resource[agent1,key=key6]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	63cf9e5d-9770-4b9f-adbb-9054902ca9dc	test::Resource[agent1,key=key1]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	5040217a-04f4-48aa-a44b-7905f2cd6f63	test::Fail[agent1,key=key2]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	a5b300ef-d2c5-49c4-85d8-eceee52e8a0f	test::Resource[agent1,key=key3]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	9da5d094-de9d-4bc8-a294-0a3aea17ab7a	test::Fail[agent1,key=key2]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	ce53aba8-971e-4a41-8a1d-14209c860635	test::Resource[agent1,key=key1]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	dc5f2a6f-87af-4daa-8a60-ca46aa650209	test::Resource[agent1,key=key3]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	73db2e99-cc65-46e0-84af-b3ee4b3e67ce	test::Resource[agent1,key=key5]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key1]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key10]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key11]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key4]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key3]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key5]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Fail[agent1,key=key2]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key9]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	75ce0fb9-afd7-47d4-a56c-f006dca12975	test::Resource[agent1,key=key7]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	ae5ee851-6329-4d2f-800f-a710cdd1b549	test::Resource[agent1,key=key6]	1
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	3c31882f-c2d1-4104-8407-a4aad1a465ad	test::Resource[agent1,key=key11]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	1de7fe4d-1695-4f61-9a1c-d149ee38e785	test::Resource[agent1,key=key10]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	ca0b0e10-a9db-45ee-a87f-39f2d4743836	test::Resource[agent1,key=key7]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	0f14abab-2af7-43cd-a93b-4b2ff21d7a79	test::Resource[agent1,key=key9]	2
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key5]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Fail[agent1,key=key2]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key4]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key3]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key8]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key7]	3
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	51198b43-7314-4d50-a0e9-9ae4a91703d0	test::Resource[agent1,key=key1]	3
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
a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	1
863191cf-4ff9-4b06-b8da-b4793d8808c0	8
8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	863191cf-4ff9-4b06-b8da-b4793d8808c0	2026-09-18 15:48:50.776262+02	\N	7c4d44d0-5bec-47d2-a069-740ffc28b1f1
hugo-Latitude-5421	a2df72fc-4641-4e20-8e6d-28ce22a6f2bf	2026-09-18 15:48:50.908644+02	\N	08323942-eba6-4b11-b80a-e1563491db40
hugo-Latitude-5421	8e56a1a8-eaf3-456b-9250-c2a69ba8c7a7	2026-09-18 15:49:42.777828+02	2026-09-18 15:49:43.270624+02	78d1a77b-795b-4983-86ae-42b509a9e242
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202608070}
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

