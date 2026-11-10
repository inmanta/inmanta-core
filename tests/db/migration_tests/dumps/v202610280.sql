--
-- PostgreSQL database dump
--

--\restrict CkdYSwMwTfYqf1Md371bOUJSjsm9cvE3s5eV2MeSXyEj4DDZDSrsM7ZkVUgI56O

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
--SET transaction_timeout = 0;
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
    requested_environment_variables jsonb CONSTRAINT compile_environment_variables_not_null NOT NULL,
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
    inmanta_module_version character varying NOT NULL,
    extras character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL
);


--
-- Name: discoveredresource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discoveredresource (
    environment uuid CONSTRAINT unmanagedresource_environment_not_null NOT NULL,
    discovered_resource_id character varying CONSTRAINT unmanagedresource_unmanaged_resource_id_not_null NOT NULL,
    "values" jsonb CONSTRAINT unmanagedresource_values_not_null NOT NULL,
    discovered_at timestamp with time zone CONSTRAINT unmanagedresource_discovered_at_not_null NOT NULL,
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
    resources jsonb DEFAULT '{}'::jsonb,
    resource_filter jsonb,
    context jsonb
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
    category character varying DEFAULT '__None__'::character varying CONSTRAINT environmentmetricsgauge_grouped_by_not_null NOT NULL
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
    category character varying DEFAULT '__None__'::character varying CONSTRAINT environmentmetricstimer_grouped_by_not_null NOT NULL
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
    requirements character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL,
    editable_install boolean
);


--
-- Name: inmanta_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmanta_user (
    id uuid CONSTRAINT user_id_not_null NOT NULL,
    username character varying CONSTRAINT user_username_not_null NOT NULL,
    password_hash character varying CONSTRAINT user_password_hash_not_null NOT NULL,
    auth_method public.auth_method CONSTRAINT user_auth_method_not_null NOT NULL,
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
    path character varying NOT NULL
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
    resource_set uuid CONSTRAINT resource_resource_set_id_not_null NOT NULL
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
    last_handler_run character varying CONSTRAINT resource_persistent_state_deployment_result_not_null NOT NULL,
    blocked character varying CONSTRAINT resource_persistent_state_blocked_status_not_null NOT NULL,
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
    resource_set uuid CONSTRAINT resource_set_configuration_model_resource_set_id_not_null NOT NULL
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
    hostname character varying CONSTRAINT agentprocess_hostname_not_null NOT NULL,
    environment uuid CONSTRAINT agentprocess_environment_not_null NOT NULL,
    first_seen timestamp with time zone,
    expired timestamp with time zone,
    sid uuid CONSTRAINT agentprocess_sid_not_null NOT NULL
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
671fd090-ce37-4bca-8df3-fc18eccff7ef	$__scheduler	f	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	$__scheduler	f	\N
dbc13446-6cb7-45f1-834c-2c2640740f78	$__scheduler	f	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	localhost	f	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	internal	f	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	localhost	f	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	agent2	f	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	agent3	f	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	agent1	t	t
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	$__scheduler	t	t
63aa6444-1933-4f32-9f73-b7937402c167	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
1	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
1	internal	std	fa03ca24-1f73-4c78-be37-ee00241f49e1
1	localhost	fs	fa03ca24-1f73-4c78-be37-ee00241f49e1
2	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
2	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
3	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
3	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
4	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
4	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
5	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
5	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
6	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
6	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
7	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
7	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
8	localhost	fs	671fd090-ce37-4bca-8df3-fc18eccff7ef
8	localhost	std	671fd090-ce37-4bca-8df3-fc18eccff7ef
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:30.199877+01	2026-11-10 16:14:40.943934+01	2026-11-10 16:14:30.191668+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	4a887a62-e087-4d0e-889e-d1578b52f0db	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6b6716ea-18d1-41ee-adfc-2a42748176fc	fa03ca24-1f73-4c78-be37-ee00241f49e1	2026-11-10 16:14:41.16753+01	2026-11-10 16:14:49.873267+01	2026-11-10 16:14:41.149696+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	f8b8737e-ab12-4f76-b63b-8c24e78b1a5c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
d4127280-b3ce-4773-aef6-e26a7e954a88	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:50.112253+01	2026-11-10 16:14:51.043233+01	2026-11-10 16:14:50.10028+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	989a6801-9c6c-455a-bb92-ce39d63576bc	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
78d884eb-b7b0-40c8-8d5a-a90571c1d810	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:51.147617+01	2026-11-10 16:14:52.095879+01	2026-11-10 16:14:51.065187+01	{}	{"add_one_resource": "true"}	t	f	t	3	9ce11525-5c9a-4127-9e09-4a3e4b18f504	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
82a68dfb-4cf7-4226-a18c-bbf0f8824963	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:52.271173+01	2026-11-10 16:14:53.202048+01	2026-11-10 16:14:52.263889+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	c5173b4e-547a-4226-944c-53c53fc92025	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
b88571f8-5b11-4efd-b14e-610b2837fa09	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:53.306717+01	2026-11-10 16:14:54.250345+01	2026-11-10 16:14:53.250933+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	00764da4-b0db-410b-89c4-7cdbbbaa836c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
68bc3538-a6f8-4550-bdac-76406c7a9e32	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:54.35152+01	2026-11-10 16:15:02.379074+01	2026-11-10 16:14:54.341347+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	cf80fdba-6ecb-45ed-aa4e-9a1cb6ca0761	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
0c260660-c77c-4954-8643-993209373789	63aa6444-1933-4f32-9f73-b7937402c167	2026-11-10 16:15:03.337137+01	2026-11-10 16:15:03.342611+01	2026-11-10 16:15:03.324355+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	2d4db2e8-1197-43a6-ad32-e350a2e235ad	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
2	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2026-11-10 16:15:03.036257+01	t	\N	9	\N	t	\N	\N
1	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:40.921565+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	fa03ca24-1f73-4c78-be37-ee00241f49e1	2026-11-10 16:14:49.860866+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:51.030609+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2026-11-10 16:15:03.197428+01	f	\N	7	\N	t	\N	\N
3	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:52.081725+01	t	{"export_metadata": {"type": "manual", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:53.190822+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:54.239195+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:15:02.364366+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:15:02.528775+01	t	\N	3	6	t	\N	\N
8	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:15:02.693085+01	t	\N	2	7	t	\N	\N
1	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2026-11-10 16:15:02.88752+01	t	\N	6	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	1	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	1	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	1	fs	1.2.0	{}
fa03ca24-1f73-4c78-be37-ee00241f49e1	1	mitogen	0.2.5	{}
fa03ca24-1f73-4c78-be37-ee00241f49e1	1	std	7.0.0	{}
fa03ca24-1f73-4c78-be37-ee00241f49e1	1	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	2	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	2	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	2	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	3	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	3	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	3	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	4	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	4	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	4	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	5	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	5	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	5	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	6	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	6	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	6	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	std	8.7.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	8	fs	1.2.0	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	8	mitogen	0.2.5	{}
671fd090-ce37-4bca-8df3-fc18eccff7ef	8	std	8.7.5	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	discovery::Discovered[myagent,name=discovered]	{}	2026-11-10 16:15:03.203712+01	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
671fd090-ce37-4bca-8df3-fc18eccff7ef	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-11-10 16:15:03.20374+01	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
ecb5c870-c729-4ee9-a17f-3e41088a57d2	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	2026-11-10 16:15:03.02681+01	6	0	{"3909386d-b98e-540c-99ff-f24ee45263fb": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "51ea1e9d-57a9-5930-bfb4-bcb422aadeb0": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "63b97f38-939b-58c6-b989-2a447d881805": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "8a95324b-5278-5e5d-9462-dfe014310ef2": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}}, "a6047cd2-6a82-5d6c-9905-551e9028395e": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "a83bc742-3fa6-5372-a434-64f73b8b8fe2": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
dbc13446-6cb7-45f1-834c-2c2640740f78	dev-2	52b80799-a1ae-4e71-9b27-adf84260c0f9			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
fa03ca24-1f73-4c78-be37-ee00241f49e1	dev-1-twin	52b80799-a1ae-4e71-9b27-adf84260c0f9			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
671fd090-ce37-4bca-8df3-fc18eccff7ef	dev-1	52b80799-a1ae-4e71-9b27-adf84260c0f9			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	dev-3	52b80799-a1ae-4e71-9b27-adf84260c0f9			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
63aa6444-1933-4f32-9f73-b7937402c167	dev-4	52b80799-a1ae-4e71-9b27-adf84260c0f9			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
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
mitogen	0.2.5	671fd090-ce37-4bca-8df3-fc18eccff7ef	{}	f
std	8.7.5	671fd090-ce37-4bca-8df3-fc18eccff7ef	{}	f
fs	1.2.0	671fd090-ce37-4bca-8df3-fc18eccff7ef	{}	f
mitogen	0.2.5	fa03ca24-1f73-4c78-be37-ee00241f49e1	{}	f
std	7.0.0	fa03ca24-1f73-4c78-be37-ee00241f49e1	{}	f
fs	1.2.0	fa03ca24-1f73-4c78-be37-ee00241f49e1	{}	f
\.


--
-- Data for Name: inmanta_user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inmanta_user (id, username, password_hash, auth_method, is_admin) FROM stdin;
\.


--
-- Data for Name: module_files; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.module_files (inmanta_module_name, inmanta_module_version, environment, file_content_hash, path) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification (id, environment, created, title, message, severity, uri, read, cleared, compile_id) FROM stdin;
8739b4fa-3a7e-4fc7-92e3-85641c005ce3	63aa6444-1933-4f32-9f73-b7937402c167	2026-11-10 16:15:03.344257+01	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/0c260660-c77c-4954-8643-993209373789	f	f	0c260660-c77c-4954-8643-993209373789
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
69f2cf9c-a431-4a34-ac85-cd0aad42f113	fact1	value1	671fd090-ce37-4bca-8df3-fc18eccff7ef	std::testing::NullResource[localhost,name=test1]	fact	2026-11-10 16:14:53.233918+01	{}	f
07401e6b-9322-472c-a902-0889523942fb	fact2	value2	671fd090-ce37-4bca-8df3-fc18eccff7ef	std::testing::NullResource[localhost,name=test2]	fact	2026-11-10 16:14:53.237036+01	{}	t
297bb39c-5587-471d-a8e8-2ea79abd21be	fact3	value3	671fd090-ce37-4bca-8df3-fc18eccff7ef	std::testing::NullResource[localhost,name=test3]	fact	2026-11-10 16:14:53.240788+01	{}	t
bb7f025b-b42a-4b47-b442-b8baa5d83d73	parameter1	value1	671fd090-ce37-4bca-8df3-fc18eccff7ef		fact	2026-11-10 16:14:53.243568+01	{}	f
c316255b-f65e-48ad-a516-b341c7a875b9	parameter2	value2	671fd090-ce37-4bca-8df3-fc18eccff7ef		fact	2026-11-10 16:14:53.246171+01	{}	f
3315871d-ff98-4ceb-a609-adf6a314ec09	parameter3	value3	671fd090-ce37-4bca-8df3-fc18eccff7ef		fact	2026-11-10 16:14:53.248669+01	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
52b80799-a1ae-4e71-9b27-adf84260c0f9	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
bc730452-26b2-43bf-85fb-09cc23905eb5	2026-11-10 16:14:40.018885+01	2026-11-10 16:14:40.943425+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdlx2sfww --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.027 seconds\ncompiler       DEBUG   The entire export command took 0.070 seconds\n	0	b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a
335bf7a0-f38f-49f7-a2c6-b919dad1a8a6	2026-11-10 16:14:30.200283+01	2026-11-10 16:14:30.202656+01		Init		Using extra environment variables during compile \n	0	b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a
377e7f9e-a3dc-4fe1-8859-a3dd35caf7f3	2026-11-10 16:14:30.202969+01	2026-11-10 16:14:30.204577+01		Venv check		Creating new venv at /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env-py3.14\n	0	b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a
233a256e-6bc6-4a5a-b3b6-c378f3ff6ae9	2026-11-10 16:14:30.206431+01	2026-11-10 16:14:30.405497+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a
7d507191-ed77-4ecc-ad05-a7f542544e19	2026-11-10 16:14:41.168346+01	2026-11-10 16:14:41.175566+01		Init		Using extra environment variables during compile \n	0	6b6716ea-18d1-41ee-adfc-2a42748176fc
896f9bf5-5d0e-4978-8736-4f5b3d618039	2026-11-10 16:14:41.17614+01	2026-11-10 16:14:41.178981+01		Venv check		Creating new venv at /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env-py3.14\n	0	6b6716ea-18d1-41ee-adfc-2a42748176fc
2ce3b2ed-9772-466c-a5d6-cd68b7fba953	2026-11-10 16:14:30.405881+01	2026-11-10 16:14:40.018504+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp6ovfab60:\n                                 Pip command: /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp6ovfab60 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, python-dateutil, mitogen, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.6\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.54 python-dateutil-3.0.0 tornado-6.6.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	b8dd5ab3-0e41-4b75-b9ff-5e398f5f318a
8950b918-451c-41e6-82d3-3141f6aaa1ff	2026-11-10 16:14:51.149563+01	2026-11-10 16:14:51.158407+01		Init		Using extra environment variables during compile add_one_resource='true'\n	0	78d884eb-b7b0-40c8-8d5a-a90571c1d810
8c9940e7-ae4d-43e8-a78a-2f7b1c214712	2026-11-10 16:14:41.180871+01	2026-11-10 16:14:41.38229+01	/tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6b6716ea-18d1-41ee-adfc-2a42748176fc
007d7017-8e29-4e10-8dbb-949006e38dea	2026-11-10 16:14:51.159566+01	2026-11-10 16:14:51.161786+01		Venv check		Found existing venv\n	0	78d884eb-b7b0-40c8-8d5a-a90571c1d810
3d879fe9-0f54-4972-9186-e5f04cb8b597	2026-11-10 16:14:53.30844+01	2026-11-10 16:14:53.31667+01		Init		Using extra environment variables during compile \n	0	b88571f8-5b11-4efd-b14e-610b2837fa09
55e6bac9-fc07-467d-a4ba-3b4b927c0de1	2026-11-10 16:14:51.16283+01	2026-11-10 16:14:52.095469+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmp5mscp_2o --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.019 seconds\ncompiler       DEBUG   The entire export command took 0.063 seconds\n	0	78d884eb-b7b0-40c8-8d5a-a90571c1d810
988dfb4f-7785-450e-969d-a18e598b5039	2026-11-10 16:14:52.272207+01	2026-11-10 16:14:52.274834+01		Init		Using extra environment variables during compile \n	0	82a68dfb-4cf7-4226-a18c-bbf0f8824963
e0c0dfb9-8355-48bc-8deb-fc388a2783ca	2026-11-10 16:14:54.354368+01	2026-11-10 16:14:54.354977+01		Venv check		Found existing venv\n	0	68bc3538-a6f8-4550-bdac-76406c7a9e32
e36475ec-6014-429a-a758-0d238b238a2e	2026-11-10 16:14:52.275094+01	2026-11-10 16:14:52.275518+01		Venv check		Found existing venv\n	0	82a68dfb-4cf7-4226-a18c-bbf0f8824963
4a5b67a0-201b-45ae-ae8b-430d08c9503e	2026-11-10 16:14:53.317616+01	2026-11-10 16:14:53.319522+01		Venv check		Found existing venv\n	0	b88571f8-5b11-4efd-b14e-610b2837fa09
c9528893-347d-4548-81ed-76d0d7217e5c	2026-11-10 16:14:52.275691+01	2026-11-10 16:14:53.201577+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp7wmwzson --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.061 seconds\n	0	82a68dfb-4cf7-4226-a18c-bbf0f8824963
579b55ac-051b-464c-bb54-2d131adef525	2026-11-10 16:14:53.32037+01	2026-11-10 16:14:54.249858+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpq_y0zzgc --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.058 seconds\n	0	b88571f8-5b11-4efd-b14e-610b2837fa09
6cf7dc0d-7c87-4469-b4f9-fe2cd5e395fe	2026-11-10 16:14:54.351822+01	2026-11-10 16:14:54.354043+01		Init		Using extra environment variables during compile \n	0	68bc3538-a6f8-4550-bdac-76406c7a9e32
68342c57-e723-42f2-b03c-979cef34a636	2026-11-10 16:14:54.356411+01	2026-11-10 16:14:54.55334+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	68bc3538-a6f8-4550-bdac-76406c7a9e32
ffa4a6e8-6ff0-4f19-946d-75d89750f481	2026-11-10 16:14:50.116625+01	2026-11-10 16:14:51.042904+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp22gs3qeq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	d4127280-b3ce-4773-aef6-e26a7e954a88
a07d554f-764f-46e4-98c1-e849823ae089	2026-11-10 16:14:41.382671+01	2026-11-10 16:14:48.974168+01	/tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmptpe7gzzk:\n                                 Pip command: /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmptpe7gzzk inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, python-dateutil, mitogen, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.6\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.54 python-dateutil-3.0.0 tornado-6.6.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	6b6716ea-18d1-41ee-adfc-2a42748176fc
283d8eeb-11ed-49db-95e8-a21654d5ca6a	2026-11-10 16:14:48.974729+01	2026-11-10 16:14:49.872923+01	/tmp/tmp0obrjioq/server/fa03ca24-1f73-4c78-be37-ee00241f49e1/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e fa03ca24-1f73-4c78-be37-ee00241f49e1 --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3sy9wp76 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	6b6716ea-18d1-41ee-adfc-2a42748176fc
37cc108a-6328-4d05-b2b0-8227ee96b321	2026-11-10 16:14:50.112933+01	2026-11-10 16:14:50.115587+01		Init		Using extra environment variables during compile \n	0	d4127280-b3ce-4773-aef6-e26a7e954a88
54d4143a-d34b-4290-8a60-29c2fe24fdd6	2026-11-10 16:14:50.115896+01	2026-11-10 16:14:50.116455+01		Venv check		Found existing venv\n	0	d4127280-b3ce-4773-aef6-e26a7e954a88
1e3723b3-0354-42fa-a1da-90bc073e8c99	2026-11-10 16:15:01.456858+01	2026-11-10 16:15:02.378636+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 671fd090-ce37-4bca-8df3-fc18eccff7ef --server_address localhost --server_port 44509 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpe96ex3t9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44509/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44509/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.060 seconds\n	0	68bc3538-a6f8-4550-bdac-76406c7a9e32
47151eca-8714-4352-8b37-d6bb774948e8	2026-11-10 16:14:54.553956+01	2026-11-10 16:15:01.456355+01	/tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpjii0z3cc:\n                                 Pip command: /tmp/tmp0obrjioq/server/671fd090-ce37-4bca-8df3-fc18eccff7ef/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpjii0z3cc inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	68bc3538-a6f8-4550-bdac-76406c7a9e32
e8663b89-ac25-4e3b-96ee-55466b7b28cd	2026-11-10 16:15:03.338319+01	2026-11-10 16:15:03.342138+01		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp0obrjioq/server/63aa6444-1933-4f32-9f73-b7937402c167/compiler and no repository set.\n	1	0c260660-c77c-4954-8643-993209373789
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	4cbc20ad-d7bc-46ed-b823-6152cc010a86
fa03ca24-1f73-4c78-be37-ee00241f49e1	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	40bf024c-c831-4650-83ff-86230c515c38
fa03ca24-1f73-4c78-be37-ee00241f49e1	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	40bf024c-c831-4650-83ff-86230c515c38
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6a4b192a-4943-4171-a26e-bfd9d3ce8107
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	46acc6c0-4ae0-4b61-9f58-e46152d9debe
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	46acc6c0-4ae0-4b61-9f58-e46152d9debe
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b30d33d6-00f9-43d9-8fee-2d2794f1f1f3
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	797bc134-c095-4456-9ca2-b85af3078494
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	1bcaae69-7617-42b2-9cfb-b4ea18a39756
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	9253f773-e7d0-4871-ace0-830c76a56379
671fd090-ce37-4bca-8df3-fc18eccff7ef	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	aceeaab2-6056-4a6a-b71b-cf8f7f7cc83e
671fd090-ce37-4bca-8df3-fc18eccff7ef	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	37fce061-65ad-4b71-b0e8-1df321b05da3
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	71586a46-c167-47b6-bf80-5bd51ca09fe0
671fd090-ce37-4bca-8df3-fc18eccff7ef	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	70f0fbb2-421c-496a-8547-7dcb958dfbb6
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
8541d3b7-448f-4fed-bf06-fde7a0b73db1	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-11-10 16:15:03.114995+01
4f4cd03c-ce14-4010-b18b-f9e35f3238c5	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-11-10 16:15:03.119885+01
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key11]	2026-11-10 16:15:03.114995+01	\N	2026-11-10 16:15:03.114995+01	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:03.05381+01	f	8541d3b7-448f-4fed-bf06-fde7a0b73db1	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test]	2026-11-10 16:14:41.022262+01	\N	2026-11-10 16:14:41.022262+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:14:41.013133+01	f	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key1]	2026-11-10 16:15:02.90297+01	2026-11-10 16:15:02.896657+01	2026-11-10 16:15:02.90297+01	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:02.89161+01	t	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key10]	2026-11-10 16:15:03.119885+01	\N	2026-11-10 16:15:03.119885+01	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:03.05381+01	f	4f4cd03c-ce14-4010-b18b-f9e35f3238c5	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	std::AgentConfig[internal,agentname=localhost]	2026-11-10 16:14:49.981954+01	\N	2026-11-10 16:14:49.981954+01	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:14:49.968667+01	f	\N	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	fs::File[localhost,path=/tmp/test]	2026-11-10 16:14:49.986898+01	\N	2026-11-10 16:14:49.986898+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:14:49.968667+01	f	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Fail[agent1,key=key2]	2026-11-10 16:15:02.910535+01	\N	2026-11-10 16:15:02.910535+01	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:15:02.89161+01	f	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key7]	2026-11-10 16:15:03.12426+01	2026-11-10 16:15:03.120967+01	2026-11-10 16:15:03.12426+01	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:03.05381+01	t	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key3]	2026-11-10 16:15:02.9124+01	\N	2026-11-10 16:15:02.9124+01	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-11-10 16:15:02.89161+01	f	\N	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	fs::File[localhost,path=/tmp/test_orphan]	2026-11-10 16:14:52.147986+01	\N	2026-11-10 16:14:52.147986+01	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:14:52.136358+01	f	\N	3
671fd090-ce37-4bca-8df3-fc18eccff7ef	test::Resource[agent2,key=key2]	2026-11-10 16:15:02.564387+01	\N	2026-11-10 16:15:02.564387+01	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:15:02.55635+01	f	\N	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	test::Resource[agent3,key=key3]	2026-11-10 16:15:02.566376+01	\N	2026-11-10 16:15:02.566376+01	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-11-10 16:15:02.55635+01	f	\N	7
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-11-10 16:15:02.89161+01	\N	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-11-10 16:15:02.89161+01	\N	\N	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key6]	2026-11-10 16:15:02.907698+01	2026-11-10 16:15:02.904241+01	2026-11-10 16:15:02.907698+01	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:02.89161+01	t	\N	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	test::Resource[agent1,key=key9]	2026-11-10 16:15:03.105901+01	2026-11-10 16:15:03.09193+01	2026-11-10 16:15:03.105901+01	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 16:15:03.05381+01	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	4cbc20ad-d7bc-46ed-b823-6152cc010a86	\N
fa03ca24-1f73-4c78-be37-ee00241f49e1	40bf024c-c831-4650-83ff-86230c515c38	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	6a4b192a-4943-4171-a26e-bfd9d3ce8107	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	46acc6c0-4ae0-4b61-9f58-e46152d9debe	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	b30d33d6-00f9-43d9-8fee-2d2794f1f1f3	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	797bc134-c095-4456-9ca2-b85af3078494	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	1bcaae69-7617-42b2-9cfb-b4ea18a39756	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	9253f773-e7d0-4871-ace0-830c76a56379	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	aceeaab2-6056-4a6a-b71b-cf8f7f7cc83e	set-a
671fd090-ce37-4bca-8df3-fc18eccff7ef	37fce061-65ad-4b71-b0e8-1df321b05da3	set-b
671fd090-ce37-4bca-8df3-fc18eccff7ef	71586a46-c167-47b6-bf80-5bd51ca09fe0	\N
671fd090-ce37-4bca-8df3-fc18eccff7ef	70f0fbb2-421c-496a-8547-7dcb958dfbb6	set-a
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	3600ee18-0218-4b2d-af65-ebf4610f6b13	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	50379efd-9132-4fd7-8d44-d340366d2ca3	\N
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	1	4cbc20ad-d7bc-46ed-b823-6152cc010a86
fa03ca24-1f73-4c78-be37-ee00241f49e1	1	40bf024c-c831-4650-83ff-86230c515c38
671fd090-ce37-4bca-8df3-fc18eccff7ef	2	6a4b192a-4943-4171-a26e-bfd9d3ce8107
671fd090-ce37-4bca-8df3-fc18eccff7ef	3	46acc6c0-4ae0-4b61-9f58-e46152d9debe
671fd090-ce37-4bca-8df3-fc18eccff7ef	4	b30d33d6-00f9-43d9-8fee-2d2794f1f1f3
671fd090-ce37-4bca-8df3-fc18eccff7ef	5	797bc134-c095-4456-9ca2-b85af3078494
671fd090-ce37-4bca-8df3-fc18eccff7ef	6	1bcaae69-7617-42b2-9cfb-b4ea18a39756
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	9253f773-e7d0-4871-ace0-830c76a56379
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	aceeaab2-6056-4a6a-b71b-cf8f7f7cc83e
671fd090-ce37-4bca-8df3-fc18eccff7ef	7	37fce061-65ad-4b71-b0e8-1df321b05da3
671fd090-ce37-4bca-8df3-fc18eccff7ef	8	71586a46-c167-47b6-bf80-5bd51ca09fe0
671fd090-ce37-4bca-8df3-fc18eccff7ef	8	70f0fbb2-421c-496a-8547-7dcb958dfbb6
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	3600ee18-0218-4b2d-af65-ebf4610f6b13
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	50379efd-9132-4fd7-8d44-d340366d2ca3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	3	dd941f3f-fc39-47e4-bea8-2e6f7c7e6645
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
909e9d96-02ed-497c-96b1-b6a9bf37c37f	store	2026-11-10 16:14:40.921511+01	2026-11-10 16:14:40.928428+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T16:14:40.928439+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	1	{"fs::File[localhost,path=/tmp/test],v=1"}
d5549279-bcb1-4d8d-90a4-50dc5ef5d3c0	deploy	2026-11-10 16:14:41.020212+01	2026-11-10 16:14:41.022262+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:14:41.021423+01:00\\"}"}	unavailable	\N	nochange	671fd090-ce37-4bca-8df3-fc18eccff7ef	1	{"fs::File[localhost,path=/tmp/test],v=1"}
a2de41c6-52b0-4a63-aa77-135c24801b29	store	2026-11-10 16:14:49.860805+01	2026-11-10 16:14:49.863861+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T16:14:49.863871+01:00\\"}"}	\N	\N	\N	fa03ca24-1f73-4c78-be37-ee00241f49e1	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
fcc09694-ab7c-4392-8d81-abfed1763175	deploy	2026-11-10 16:14:49.975087+01	2026-11-10 16:14:49.981954+01	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:14:49.981436+01:00\\"}"}	unavailable	\N	nochange	fa03ca24-1f73-4c78-be37-ee00241f49e1	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
14f2bbdc-8528-4b76-9ffb-14b17dbb04c1	deploy	2026-11-10 16:14:49.985775+01	2026-11-10 16:14:49.986898+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:14:49.986483+01:00\\"}"}	unavailable	\N	nochange	fa03ca24-1f73-4c78-be37-ee00241f49e1	1	{"fs::File[localhost,path=/tmp/test],v=1"}
20e44394-e838-4dc6-b68c-d71dd61f357e	store	2026-11-10 16:14:51.030558+01	2026-11-10 16:14:51.032731+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-10T16:14:51.032738+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	2	{"fs::File[localhost,path=/tmp/test],v=2"}
9bd9c878-43e9-4b27-84e0-b53b1bbcadb1	store	2026-11-10 16:14:52.081678+01	2026-11-10 16:14:52.087179+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-10T16:14:52.087195+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
cecf7af5-ed03-4478-b433-bab52940652d	deploy	2026-11-10 16:14:52.140284+01	2026-11-10 16:14:52.147986+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-11-10T16:14:52.147499+01:00\\"}"}	unavailable	\N	nochange	671fd090-ce37-4bca-8df3-fc18eccff7ef	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
dc11e710-14d7-4bd9-ab86-f4fdacd26135	store	2026-11-10 16:14:53.190773+01	2026-11-10 16:14:53.192953+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-11-10T16:14:53.192961+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	4	{"fs::File[localhost,path=/tmp/test],v=4"}
d286880a-d885-4988-99e8-8c8e5a80f0ee	store	2026-11-10 16:14:54.239135+01	2026-11-10 16:14:54.241362+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-11-10T16:14:54.241370+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	5	{"fs::File[localhost,path=/tmp/test],v=5"}
77dc1090-c752-466c-9eb8-7688aaf818f6	store	2026-11-10 16:15:02.364302+01	2026-11-10 16:15:02.369608+01	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-11-10T16:15:02.369616+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	6	{"fs::File[localhost,path=/tmp/test],v=6"}
8e13618c-b83c-4848-b568-f184c0d14cad	store	2026-11-10 16:15:02.528664+01	2026-11-10 16:15:02.532478+01	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-11-10T16:15:02.532486+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent3,key=key3],v=7","test::Resource[agent2,key=key2],v=7"}
123e415b-a663-48b9-86a8-f6b19f1b1b73	deploy	2026-11-10 16:15:02.561903+01	2026-11-10 16:15:02.564387+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.563788+01:00\\"}"}	unavailable	\N	nochange	671fd090-ce37-4bca-8df3-fc18eccff7ef	7	{"test::Resource[agent2,key=key2],v=7"}
732817f5-aa86-4242-8d70-6a8827293c99	deploy	2026-11-10 16:15:02.564439+01	2026-11-10 16:15:02.566376+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.565881+01:00\\"}"}	unavailable	\N	nochange	671fd090-ce37-4bca-8df3-fc18eccff7ef	7	{"test::Resource[agent3,key=key3],v=7"}
25d6d54d-0c60-4bd7-81cb-2f90f08bd697	store	2026-11-10 16:15:02.692576+01	2026-11-10 16:15:02.710496+01	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-11-10T16:15:02.710514+01:00\\"}"}	\N	\N	\N	671fd090-ce37-4bca-8df3-fc18eccff7ef	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
37801b27-07f2-458a-806e-7eed0a7a9fbe	store	2026-11-10 16:15:02.887457+01	2026-11-10 16:15:02.889415+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T16:15:02.889422+01:00\\"}"}	\N	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key1],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key4],v=1"}
a0847bbf-12f4-4c03-8746-33d5f56c3f96	deploy	2026-11-10 16:15:02.8967+01	2026-11-10 16:15:02.90297+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: bca4879c-6a8e-4d9b-9519-bbcaa6e44034).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"bca4879c-6a8e-4d9b-9519-bbcaa6e44034\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.897532+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: bca4879c-6a8e-4d9b-9519-bbcaa6e44034) - duration: 0.0053 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.005333900451660156, \\"deploy_id\\": \\"bca4879c-6a8e-4d9b-9519-bbcaa6e44034\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.902922+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key1],v=1"}
f00114b1-1b68-4802-8511-c1131bb11d44	deploy	2026-11-10 16:15:02.90427+01	2026-11-10 16:15:02.907698+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: e4b6d6a2-87a2-4d5c-bd68-0147bd3a6852).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"e4b6d6a2-87a2-4d5c-bd68-0147bd3a6852\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.904908+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: e4b6d6a2-87a2-4d5c-bd68-0147bd3a6852) - duration: 0.0027 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0027103424072265625, \\"deploy_id\\": \\"e4b6d6a2-87a2-4d5c-bd68-0147bd3a6852\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.907666+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key6],v=1"}
f150a086-1b10-4fe0-86be-d97b1e446bcd	deploy	2026-11-10 16:15:02.908534+01	2026-11-10 16:15:02.910535+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: cf3ec9d8-f210-4cc7-b4ab-bc5ca2a33698).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"cf3ec9d8-f210-4cc7-b4ab-bc5ca2a33698\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.909171+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/tests/conftest.py\\\\\\", line 2600, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.909981+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: cf3ec9d8-f210-4cc7-b4ab-bc5ca2a33698) - duration: 0.0013 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0012822151184082031, \\"deploy_id\\": \\"cf3ec9d8-f210-4cc7-b4ab-bc5ca2a33698\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.910507+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Fail[agent1,key=key2],v=1"}
6438f05b-5416-4090-ab8b-ea1fbe46ce10	deploy	2026-11-10 16:15:02.911444+01	2026-11-10 16:15:02.9124+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 6fd08b3b-933d-4a73-ad1e-99058da8d741).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"6fd08b3b-933d-4a73-ad1e-99058da8d741\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.912020+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.912199+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 6fd08b3b-933d-4a73-ad1e-99058da8d741) - duration: 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00031638145446777344, \\"deploy_id\\": \\"6fd08b3b-933d-4a73-ad1e-99058da8d741\\"}, \\"timestamp\\": \\"2026-11-10T16:15:02.912376+01:00\\"}"}	skipped	\N	nochange	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key3],v=1"}
51618a26-e10e-4576-b2fd-c666f1104d73	dryrun	2026-11-10 16:15:03.031994+01	2026-11-10 16:15:03.033157+01	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.032049+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2 - duration 0.0010 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0010383129119873047, \\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.033137+01:00\\"}"}	dry	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Fail[agent1,key=key2],v=1"}
ea9d7cf4-f5fd-4f46-83d1-7406a443e21e	dryrun	2026-11-10 16:15:03.036742+01	2026-11-10 16:15:03.037301+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.036787+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0004603862762451172, \\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.037286+01:00\\"}"}	dry	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key1],v=1"}
b118a940-1126-4fa5-9edd-6d38fcbd8e55	dryrun	2026-11-10 16:15:03.039158+01	2026-11-10 16:15:03.039685+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.039210+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00042510032653808594, \\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.039674+01:00\\"}"}	dry	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key3],v=1"}
903f9c14-af65-4125-9c81-e6d7a2ba44da	dryrun	2026-11-10 16:15:03.041521+01	2026-11-10 16:15:03.041839+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.041565+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00022602081298828125, \\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.041828+01:00\\"}"}	dry	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key5],v=1"}
6e47b49b-5a1d-4867-b2b4-a187805eda19	dryrun	2026-11-10 16:15:03.043977+01	2026-11-10 16:15:03.044306+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.044019+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: ecb5c870-c729-4ee9-a17f-3e41088a57d2 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002338886260986328, \\"dry_run_id\\": \\"ecb5c870-c729-4ee9-a17f-3e41088a57d2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.044291+01:00\\"}"}	dry	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	1	{"test::Resource[agent1,key=key6],v=1"}
ef9c3781-75cb-441a-b224-683eedf473f7	store	2026-11-10 16:15:03.036166+01	2026-11-10 16:15:03.047898+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-10T16:15:03.047905+01:00\\"}"}	\N	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	{"test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key5],v=2"}
5bdb3a0b-f2a1-4a9a-9461-b2e283765175	deploy	2026-11-10 16:15:03.092021+01	2026-11-10 16:15:03.105901+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 89cc5c3f-fdb2-44e1-8ae3-e7e302e65b09).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"89cc5c3f-fdb2-44e1-8ae3-e7e302e65b09\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.098233+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 89cc5c3f-fdb2-44e1-8ae3-e7e302e65b09) - duration: 0.0075 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.007464170455932617, \\"deploy_id\\": \\"89cc5c3f-fdb2-44e1-8ae3-e7e302e65b09\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.105824+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	{"test::Resource[agent1,key=key9],v=2"}
19b1dafe-1430-457c-9a11-6e77d76c645f	deploy	2026-11-10 16:15:03.108147+01	2026-11-10 16:15:03.114995+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 46db4285-1b12-4484-9589-8bf803b1092d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"46db4285-1b12-4484-9589-8bf803b1092d\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.109743+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.110077+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 46db4285-1b12-4484-9589-8bf803b1092d) - duration: 0.0051 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.0051381587982177734, \\"deploy_id\\": \\"46db4285-1b12-4484-9589-8bf803b1092d\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.114950+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	{"test::Resource[agent1,key=key11],v=2"}
46383d91-2b22-4396-9129-0b0f4a912342	deploy	2026-11-10 16:15:03.116449+01	2026-11-10 16:15:03.119885+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: bd1aadba-8f0c-45f1-a0f5-2bb3a624e0a4).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"bd1aadba-8f0c-45f1-a0f5-2bb3a624e0a4\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.117072+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.117312+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: bd1aadba-8f0c-45f1-a0f5-2bb3a624e0a4) - duration: 0.0027 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0027375221252441406, \\"deploy_id\\": \\"bd1aadba-8f0c-45f1-a0f5-2bb3a624e0a4\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.119856+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	{"test::Resource[agent1,key=key10],v=2"}
9bb78461-04c5-4a76-9809-40c0c9409704	deploy	2026-11-10 16:15:03.120993+01	2026-11-10 16:15:03.12426+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 96ca82cf-6be7-4273-9d3d-c029ff276326).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"96ca82cf-6be7-4273-9d3d-c029ff276326\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.121588+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 96ca82cf-6be7-4273-9d3d-c029ff276326) - duration: 0.0026 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0026001930236816406, \\"deploy_id\\": \\"96ca82cf-6be7-4273-9d3d-c029ff276326\\"}, \\"timestamp\\": \\"2026-11-10T16:15:03.124230+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2	{"test::Resource[agent1,key=key7],v=2"}
c403105c-0e4d-456b-b9fc-d7522978cb55	store	2026-11-10 16:15:03.197205+01	2026-11-10 16:15:03.199412+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-10T16:15:03.199420+01:00\\"}"}	\N	\N	\N	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	3	{"test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
671fd090-ce37-4bca-8df3-fc18eccff7ef	909e9d96-02ed-497c-96b1-b6a9bf37c37f	fs::File[localhost,path=/tmp/test]	1
671fd090-ce37-4bca-8df3-fc18eccff7ef	d5549279-bcb1-4d8d-90a4-50dc5ef5d3c0	fs::File[localhost,path=/tmp/test]	1
fa03ca24-1f73-4c78-be37-ee00241f49e1	a2de41c6-52b0-4a63-aa77-135c24801b29	fs::File[localhost,path=/tmp/test]	1
fa03ca24-1f73-4c78-be37-ee00241f49e1	a2de41c6-52b0-4a63-aa77-135c24801b29	std::AgentConfig[internal,agentname=localhost]	1
fa03ca24-1f73-4c78-be37-ee00241f49e1	fcc09694-ab7c-4392-8d81-abfed1763175	std::AgentConfig[internal,agentname=localhost]	1
fa03ca24-1f73-4c78-be37-ee00241f49e1	14f2bbdc-8528-4b76-9ffb-14b17dbb04c1	fs::File[localhost,path=/tmp/test]	1
671fd090-ce37-4bca-8df3-fc18eccff7ef	20e44394-e838-4dc6-b68c-d71dd61f357e	fs::File[localhost,path=/tmp/test]	2
671fd090-ce37-4bca-8df3-fc18eccff7ef	9bd9c878-43e9-4b27-84e0-b53b1bbcadb1	fs::File[localhost,path=/tmp/test_orphan]	3
671fd090-ce37-4bca-8df3-fc18eccff7ef	9bd9c878-43e9-4b27-84e0-b53b1bbcadb1	fs::File[localhost,path=/tmp/test]	3
671fd090-ce37-4bca-8df3-fc18eccff7ef	cecf7af5-ed03-4478-b433-bab52940652d	fs::File[localhost,path=/tmp/test_orphan]	3
671fd090-ce37-4bca-8df3-fc18eccff7ef	dc11e710-14d7-4bd9-ab86-f4fdacd26135	fs::File[localhost,path=/tmp/test]	4
671fd090-ce37-4bca-8df3-fc18eccff7ef	d286880a-d885-4988-99e8-8c8e5a80f0ee	fs::File[localhost,path=/tmp/test]	5
671fd090-ce37-4bca-8df3-fc18eccff7ef	77dc1090-c752-466c-9eb8-7688aaf818f6	fs::File[localhost,path=/tmp/test]	6
671fd090-ce37-4bca-8df3-fc18eccff7ef	8e13618c-b83c-4848-b568-f184c0d14cad	fs::File[localhost,path=/tmp/test]	7
671fd090-ce37-4bca-8df3-fc18eccff7ef	8e13618c-b83c-4848-b568-f184c0d14cad	test::Resource[agent3,key=key3]	7
671fd090-ce37-4bca-8df3-fc18eccff7ef	8e13618c-b83c-4848-b568-f184c0d14cad	test::Resource[agent2,key=key2]	7
671fd090-ce37-4bca-8df3-fc18eccff7ef	123e415b-a663-48b9-86a8-f6b19f1b1b73	test::Resource[agent2,key=key2]	7
671fd090-ce37-4bca-8df3-fc18eccff7ef	732817f5-aa86-4242-8d70-6a8827293c99	test::Resource[agent3,key=key3]	7
671fd090-ce37-4bca-8df3-fc18eccff7ef	25d6d54d-0c60-4bd7-81cb-2f90f08bd697	fs::File[localhost,path=/tmp/test]	8
671fd090-ce37-4bca-8df3-fc18eccff7ef	25d6d54d-0c60-4bd7-81cb-2f90f08bd697	test::Resource[agent2,key=key2]	8
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Resource[agent1,key=key3]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Resource[agent1,key=key5]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Resource[agent1,key=key1]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Fail[agent1,key=key2]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Resource[agent1,key=key6]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	37801b27-07f2-458a-806e-7eed0a7a9fbe	test::Resource[agent1,key=key4]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	a0847bbf-12f4-4c03-8746-33d5f56c3f96	test::Resource[agent1,key=key1]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	f00114b1-1b68-4802-8511-c1131bb11d44	test::Resource[agent1,key=key6]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	f150a086-1b10-4fe0-86be-d97b1e446bcd	test::Fail[agent1,key=key2]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	6438f05b-5416-4090-ab8b-ea1fbe46ce10	test::Resource[agent1,key=key3]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	51618a26-e10e-4576-b2fd-c666f1104d73	test::Fail[agent1,key=key2]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ea9d7cf4-f5fd-4f46-83d1-7406a443e21e	test::Resource[agent1,key=key1]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	b118a940-1126-4fa5-9edd-6d38fcbd8e55	test::Resource[agent1,key=key3]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	903f9c14-af65-4125-9c81-e6d7a2ba44da	test::Resource[agent1,key=key5]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	6e47b49b-5a1d-4867-b2b4-a187805eda19	test::Resource[agent1,key=key6]	1
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Fail[agent1,key=key2]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key7]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key10]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key4]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key11]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key3]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key9]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key1]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	ef9c3781-75cb-441a-b224-683eedf473f7	test::Resource[agent1,key=key5]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	5bdb3a0b-f2a1-4a9a-9461-b2e283765175	test::Resource[agent1,key=key9]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	19b1dafe-1430-457c-9a11-6e77d76c645f	test::Resource[agent1,key=key11]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	46383d91-2b22-4396-9129-0b0f4a912342	test::Resource[agent1,key=key10]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	9bb78461-04c5-4a76-9809-40c0c9409704	test::Resource[agent1,key=key7]	2
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Fail[agent1,key=key2]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key1]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key4]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key7]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key5]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key8]	3
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	c403105c-0e4d-456b-b9fc-d7522978cb55	test::Resource[agent1,key=key3]	3
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
fa03ca24-1f73-4c78-be37-ee00241f49e1	1
671fd090-ce37-4bca-8df3-fc18eccff7ef	8
9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	671fd090-ce37-4bca-8df3-fc18eccff7ef	2026-11-10 16:14:29.944633+01	\N	94fcd0f9-16db-45b3-ad3c-7011d262f4eb
arnaud-inmanta-laptop	fa03ca24-1f73-4c78-be37-ee00241f49e1	2026-11-10 16:14:30.058642+01	\N	3e75c015-0795-4a73-9599-bdfcfbbbcbb3
arnaud-inmanta-laptop	9b70c446-c476-43b4-bcd4-0e1adf02ef1c	2026-11-10 16:15:02.752621+01	2026-11-10 16:15:03.189539+01	ec9ca1c5-c434-4176-af6b-997ec9475b1d
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610161,202610280}
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
    ADD CONSTRAINT module_files_pkey PRIMARY KEY (environment, inmanta_module_name, inmanta_module_version, path);


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
-- Name: configurationmodel_modules_env_module_name_module_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX configurationmodel_modules_env_module_name_module_version_index ON public.configurationmodel_modules USING btree (environment, inmanta_module_name, inmanta_module_version);


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
-- Name: agent_modules agent_modules_environment_cm_version_inmanta_module_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_cm_version_inmanta_module_name_fkey FOREIGN KEY (environment, cm_version, inmanta_module_name) REFERENCES public.configurationmodel_modules(environment, cm_version, inmanta_module_name) ON DELETE CASCADE;


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
-- Name: configurationmodel_modules configurationmodel_modules_env_module_name_module_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_env_module_name_module_version_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT;


--
-- Name: configurationmodel_modules configurationmodel_modules_environment_cm_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationmodel_modules
    ADD CONSTRAINT configurationmodel_modules_environment_cm_version_fkey FOREIGN KEY (environment, cm_version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


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

--\unrestrict CkdYSwMwTfYqf1Md371bOUJSjsm9cvE3s5eV2MeSXyEj4DDZDSrsM7ZkVUgI56O

