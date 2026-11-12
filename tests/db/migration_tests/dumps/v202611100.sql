--
-- PostgreSQL database dump
--

--\restrict u8w6bOGy2z8zHLFBZn5YHe5Z4CKkaWYRFf3SW6PrCQEfebuSzIWbj8Zqk84O3yR

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
-- Name: require; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.require (
    environment uuid NOT NULL,
    resource_set_dependent uuid NOT NULL,
    resource_id_dependent character varying NOT NULL,
    resource_id_dependency character varying NOT NULL
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
60256208-0349-46ce-9b2c-1893dba2a05e	$__scheduler	f	\N
af711d09-06cb-434a-881b-27af6dc765b0	$__scheduler	f	\N
18da23be-bd24-4c2f-b427-15f222cff6b8	$__scheduler	f	\N
60256208-0349-46ce-9b2c-1893dba2a05e	localhost	f	\N
af711d09-06cb-434a-881b-27af6dc765b0	internal	f	\N
af711d09-06cb-434a-881b-27af6dc765b0	localhost	f	\N
60256208-0349-46ce-9b2c-1893dba2a05e	agent2	f	\N
60256208-0349-46ce-9b2c-1893dba2a05e	agent3	f	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	agent1	t	t
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	$__scheduler	t	t
9c0d9e64-8803-435f-99e6-d5d01c3b076b	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
1	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
1	internal	std	af711d09-06cb-434a-881b-27af6dc765b0
1	localhost	fs	af711d09-06cb-434a-881b-27af6dc765b0
2	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
2	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
3	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
3	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
4	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
4	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
5	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
5	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
6	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
6	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
7	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
7	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
8	localhost	fs	60256208-0349-46ce-9b2c-1893dba2a05e
8	localhost	std	60256208-0349-46ce-9b2c-1893dba2a05e
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
e78ff650-fbf0-44d5-b318-cd39b0adfa99	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:25.841315+01	2026-11-10 15:56:36.354885+01	2026-11-10 15:56:25.833606+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	51310497-a501-44b5-8ddc-b2c5f998257e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
138dbd1d-1f05-4ea9-8737-fd6d0013f676	af711d09-06cb-434a-881b-27af6dc765b0	2026-11-10 15:56:36.547184+01	2026-11-10 15:56:45.951171+01	2026-11-10 15:56:36.526938+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	2d754bad-b051-417b-baa4-1eec09269f14	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
73b89718-c0fe-404c-b9ba-40d0af436292	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:46.174344+01	2026-11-10 15:56:47.138905+01	2026-11-10 15:56:46.163019+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	34427e8d-b88e-4290-8f00-f6eb53a09404	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
5e4c5b80-557d-40fe-bdc0-fed4cc4125af	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:47.261857+01	2026-11-10 15:56:48.250273+01	2026-11-10 15:56:47.258068+01	{}	{"add_one_resource": "true"}	t	f	t	3	b04be367-ebcf-4832-8914-d11328c7c187	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
787314e9-7cf3-431d-909d-05bc581369ef	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:48.480676+01	2026-11-10 15:56:49.453753+01	2026-11-10 15:56:48.472503+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	d3b4e9e9-872d-436c-b321-5dfbc0467042	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
2ea59481-32f2-40cb-b4c2-60015aad85b2	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:49.596528+01	2026-11-10 15:56:50.577451+01	2026-11-10 15:56:49.59151+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	4a4a8664-312c-4d54-bb10-ce9120c06bbf	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
fa4150c4-f8be-42c0-8452-2bdc164554a3	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:50.678429+01	2026-11-10 15:57:00.135703+01	2026-11-10 15:56:50.668846+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	c3de05c9-6ce1-4021-b0ba-89af104a8718	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c42f67f8-0cb6-4723-992d-73b4ae656082	9c0d9e64-8803-435f-99e6-d5d01c3b076b	2026-11-10 15:57:00.961468+01	2026-11-10 15:57:00.965114+01	2026-11-10 15:57:00.950765+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	02608525-74ed-4766-b3a0-ec47641bc818	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
2	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2026-11-10 15:57:00.668175+01	t	\N	9	\N	t	\N	\N
1	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:36.336566+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	af711d09-06cb-434a-881b-27af6dc765b0	2026-11-10 15:56:45.929065+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:47.128334+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2026-11-10 15:57:00.825642+01	f	\N	7	\N	t	\N	\N
3	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:48.225633+01	t	{"export_metadata": {"type": "manual", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:49.44202+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:50.566844+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:57:00.12393+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:57:00.172194+01	t	\N	3	6	t	\N	\N
8	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:57:00.343364+01	t	\N	2	7	t	\N	\N
1	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2026-11-10 15:57:00.535978+01	t	\N	6	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	1	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	1	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	1	fs	1.2.0	{}
af711d09-06cb-434a-881b-27af6dc765b0	1	mitogen	0.2.5	{}
af711d09-06cb-434a-881b-27af6dc765b0	1	std	7.0.0	{}
af711d09-06cb-434a-881b-27af6dc765b0	1	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	2	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	2	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	2	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	3	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	3	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	3	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	4	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	4	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	4	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	5	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	5	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	5	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	6	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	6	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	6	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	7	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	7	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	7	std	8.7.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	8	fs	1.2.0	{}
60256208-0349-46ce-9b2c-1893dba2a05e	8	mitogen	0.2.5	{}
60256208-0349-46ce-9b2c-1893dba2a05e	8	std	8.7.5	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	discovery::Discovered[myagent,name=discovered]	{}	2026-11-10 15:57:00.83087+01	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
60256208-0349-46ce-9b2c-1893dba2a05e	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-11-10 15:57:00.830892+01	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
cd4031af-969a-452f-b642-5db1d95235c1	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	2026-11-10 15:57:00.659029+01	6	0	{"25e4f8d6-9db3-5439-af22-7cff6d6f8595": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "49d45e9c-ad07-5027-bee0-c805df31a3d5": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "64e07497-6fe4-5994-8545-971c7dc7486a": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "6d86d02d-f522-5c95-ba5d-a1b14e45cd43": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}}, "d0a3289a-3939-5c7c-b2cb-facf658beee8": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "d150233b-11bd-5dd3-8cd4-0ea650bb3ba9": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
18da23be-bd24-4c2f-b427-15f222cff6b8	dev-2	1efcb3c8-7229-477b-bffb-34bf013162de			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
af711d09-06cb-434a-881b-27af6dc765b0	dev-1-twin	1efcb3c8-7229-477b-bffb-34bf013162de			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
60256208-0349-46ce-9b2c-1893dba2a05e	dev-1	1efcb3c8-7229-477b-bffb-34bf013162de			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	dev-3	1efcb3c8-7229-477b-bffb-34bf013162de			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
9c0d9e64-8803-435f-99e6-d5d01c3b076b	dev-4	1efcb3c8-7229-477b-bffb-34bf013162de			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
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
mitogen	0.2.5	60256208-0349-46ce-9b2c-1893dba2a05e	{}	f
std	8.7.5	60256208-0349-46ce-9b2c-1893dba2a05e	{}	f
fs	1.2.0	60256208-0349-46ce-9b2c-1893dba2a05e	{}	f
mitogen	0.2.5	af711d09-06cb-434a-881b-27af6dc765b0	{}	f
std	7.0.0	af711d09-06cb-434a-881b-27af6dc765b0	{}	f
fs	1.2.0	af711d09-06cb-434a-881b-27af6dc765b0	{}	f
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
c99d485d-7801-46e2-ace5-fa8cbd85bdf3	9c0d9e64-8803-435f-99e6-d5d01c3b076b	2026-11-10 15:57:00.966783+01	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/c42f67f8-0cb6-4723-992d-73b4ae656082	f	f	c42f67f8-0cb6-4723-992d-73b4ae656082
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
539d365d-9fbd-421d-9103-b35ba491e901	fact1	value1	60256208-0349-46ce-9b2c-1893dba2a05e	std::testing::NullResource[localhost,name=test1]	fact	2026-11-10 15:56:49.571229+01	{}	f
3bd96661-5bd9-4464-bb3c-0fe8a8789974	fact2	value2	60256208-0349-46ce-9b2c-1893dba2a05e	std::testing::NullResource[localhost,name=test2]	fact	2026-11-10 15:56:49.574486+01	{}	t
0980c27a-e536-40ce-9567-81afad4dba42	fact3	value3	60256208-0349-46ce-9b2c-1893dba2a05e	std::testing::NullResource[localhost,name=test3]	fact	2026-11-10 15:56:49.576974+01	{}	t
440e2dc5-8c21-45e4-a74a-652579aa6d57	parameter1	value1	60256208-0349-46ce-9b2c-1893dba2a05e		fact	2026-11-10 15:56:49.580689+01	{}	f
0b8a2d51-37b7-4398-938b-bf78bb2a9562	parameter2	value2	60256208-0349-46ce-9b2c-1893dba2a05e		fact	2026-11-10 15:56:49.584071+01	{}	f
a8917107-5c14-4478-beb7-e056785326a2	parameter3	value3	60256208-0349-46ce-9b2c-1893dba2a05e		fact	2026-11-10 15:56:49.587145+01	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
1efcb3c8-7229-477b-bffb-34bf013162de	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
21179f63-eac7-4ae1-a680-7d25b936448b	2026-11-10 15:56:25.841708+01	2026-11-10 15:56:25.84412+01		Init		Using extra environment variables during compile \n	0	e78ff650-fbf0-44d5-b318-cd39b0adfa99
cd9eefc7-3bdd-43b6-8bf3-d7c71df2d964	2026-11-10 15:56:25.844446+01	2026-11-10 15:56:25.852539+01		Venv check		Creating new venv at /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env-py3.14\n	0	e78ff650-fbf0-44d5-b318-cd39b0adfa99
b58e00f9-8d49-4ea8-b3aa-28e233068bd3	2026-11-10 15:56:25.854115+01	2026-11-10 15:56:26.269067+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e78ff650-fbf0-44d5-b318-cd39b0adfa99
733f567f-7d3e-418f-8a88-7cd58eddd235	2026-11-10 15:56:48.483353+01	2026-11-10 15:56:48.487355+01		Init		Using extra environment variables during compile \n	0	787314e9-7cf3-431d-909d-05bc581369ef
0732e80d-4f93-4b32-a43e-7760837a483e	2026-11-10 15:56:26.269671+01	2026-11-10 15:56:35.370582+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpl357ahe6:\n                                 Pip command: /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpl357ahe6 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Downloading tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 534.5/534.5 kB 82.8 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, python-dateutil, mitogen, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.6\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.54 python-dateutil-3.0.0 tornado-6.6.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	e78ff650-fbf0-44d5-b318-cd39b0adfa99
7a93f57d-9095-4090-a383-59589908dad1	2026-11-10 15:56:35.372005+01	2026-11-10 15:56:36.354436+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpx5mk8n76 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.028 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.025 seconds\ncompiler       DEBUG   The entire export command took 0.088 seconds\n	0	e78ff650-fbf0-44d5-b318-cd39b0adfa99
d60d4dce-bda3-4df8-ad7f-c1dbc5d94a31	2026-11-10 15:56:48.488064+01	2026-11-10 15:56:48.488738+01		Venv check		Found existing venv\n	0	787314e9-7cf3-431d-909d-05bc581369ef
16029120-fe14-453d-9dfa-1e32ff281a22	2026-11-10 15:56:36.547813+01	2026-11-10 15:56:36.551426+01		Init		Using extra environment variables during compile \n	0	138dbd1d-1f05-4ea9-8737-fd6d0013f676
75c97c73-3406-443a-8159-ef3f731892ae	2026-11-10 15:56:36.551985+01	2026-11-10 15:56:36.553843+01		Venv check		Creating new venv at /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env-py3.14\n	0	138dbd1d-1f05-4ea9-8737-fd6d0013f676
d6fe184f-e21d-4c15-85b4-e73e18a34b0c	2026-11-10 15:56:36.555144+01	2026-11-10 15:56:36.761232+01	/tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	138dbd1d-1f05-4ea9-8737-fd6d0013f676
0cc839bf-48a4-44a0-bdeb-8718971e0471	2026-11-10 15:56:48.48893+01	2026-11-10 15:56:49.453284+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3zxtsppz --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.059 seconds\n	0	787314e9-7cf3-431d-909d-05bc581369ef
34fd66f8-9cbc-49c9-9ee5-f25166242932	2026-11-10 15:56:50.678742+01	2026-11-10 15:56:50.680614+01		Init		Using extra environment variables during compile \n	0	fa4150c4-f8be-42c0-8452-2bdc164554a3
8bdb5aa9-ccc0-4e33-9fc2-eed9928bfc61	2026-11-10 15:56:50.68084+01	2026-11-10 15:56:50.681268+01		Venv check		Found existing venv\n	0	fa4150c4-f8be-42c0-8452-2bdc164554a3
35472dd3-17cf-4763-a328-5f932cecbade	2026-11-10 15:56:50.682627+01	2026-11-10 15:56:50.902179+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	fa4150c4-f8be-42c0-8452-2bdc164554a3
56b8457a-c10e-43b9-91ed-8cc8b3b67c58	2026-11-10 15:56:47.265955+01	2026-11-10 15:56:47.266748+01		Venv check		Found existing venv\n	0	5e4c5b80-557d-40fe-bdc0-fed4cc4125af
b494bed4-3c56-472d-ad80-0ccfc7251c53	2026-11-10 15:56:36.761669+01	2026-11-10 15:56:44.970456+01	/tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpal9va4ij:\n                                 Pip command: /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpal9va4ij inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tornado, python-dateutil, mitogen, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.6\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.54 python-dateutil-3.0.0 tornado-6.6.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	138dbd1d-1f05-4ea9-8737-fd6d0013f676
a1f147da-eeaf-4217-92cb-641c9e46961e	2026-11-10 15:56:44.97141+01	2026-11-10 15:56:45.950798+01	/tmp/tmpn1ys5ous/server/af711d09-06cb-434a-881b-27af6dc765b0/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af711d09-06cb-434a-881b-27af6dc765b0 --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp0s0lez2v --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.026 seconds\ncompiler       DEBUG   The entire export command took 0.071 seconds\n	0	138dbd1d-1f05-4ea9-8737-fd6d0013f676
34eb97dc-c6d1-4710-9b27-bf095d712883	2026-11-10 15:56:47.266931+01	2026-11-10 15:56:48.249718+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpuggqvs8j --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.028 seconds\ncompiler       DEBUG   The entire export command took 0.072 seconds\n	0	5e4c5b80-557d-40fe-bdc0-fed4cc4125af
736706fc-2197-43c8-8867-6c70690e7e64	2026-11-10 15:56:46.175123+01	2026-11-10 15:56:46.179038+01		Init		Using extra environment variables during compile \n	0	73b89718-c0fe-404c-b9ba-40d0af436292
f270f177-d1af-4008-bd55-0ce758d9b111	2026-11-10 15:56:46.17949+01	2026-11-10 15:56:46.180121+01		Venv check		Found existing venv\n	0	73b89718-c0fe-404c-b9ba-40d0af436292
b3014e21-29ba-49f5-a018-858ceaf2ee00	2026-11-10 15:56:46.180322+01	2026-11-10 15:56:47.138564+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_eaoyhy0 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.057 seconds\n	0	73b89718-c0fe-404c-b9ba-40d0af436292
c8057fdb-de03-4498-ab26-69aa38c511b3	2026-11-10 15:56:49.597704+01	2026-11-10 15:56:49.600921+01		Init		Using extra environment variables during compile \n	0	2ea59481-32f2-40cb-b4c2-60015aad85b2
a993ac0c-a196-4f4c-941d-8e3351e1691e	2026-11-10 15:56:47.262231+01	2026-11-10 15:56:47.26569+01		Init		Using extra environment variables during compile add_one_resource='true'\n	0	5e4c5b80-557d-40fe-bdc0-fed4cc4125af
c9866fa9-9d9b-42d8-a855-f4fdbc12cf87	2026-11-10 15:56:49.601223+01	2026-11-10 15:56:49.601845+01		Venv check		Found existing venv\n	0	2ea59481-32f2-40cb-b4c2-60015aad85b2
0ec7ae57-19ee-4fcd-bc89-a73e9608fdc7	2026-11-10 15:56:49.60206+01	2026-11-10 15:56:50.577062+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmprd8c1ua2 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.012 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.064 seconds\n	0	2ea59481-32f2-40cb-b4c2-60015aad85b2
0a914dab-7ad5-47a0-9e9c-8774edc3fe44	2026-11-10 15:56:50.902651+01	2026-11-10 15:56:59.147663+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp_py4yvfi:\n                                 Pip command: /tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp_py4yvfi inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	fa4150c4-f8be-42c0-8452-2bdc164554a3
e5385a32-ee4e-4185-a8b9-2ab93c86f952	2026-11-10 15:56:59.148379+01	2026-11-10 15:57:00.135332+01	/tmp/tmpn1ys5ous/server/60256208-0349-46ce-9b2c-1893dba2a05e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 60256208-0349-46ce-9b2c-1893dba2a05e --server_address localhost --server_port 60967 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppvrioy65 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:60967/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:60967/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.059 seconds\n	0	fa4150c4-f8be-42c0-8452-2bdc164554a3
4845a2e0-0b8b-4e91-af39-d2af96390c11	2026-11-10 15:57:00.962065+01	2026-11-10 15:57:00.964554+01		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpn1ys5ous/server/9c0d9e64-8803-435f-99e6-d5d01c3b076b/compiler and no repository set.\n	1	c42f67f8-0cb6-4723-992d-73b4ae656082
\.


--
-- Data for Name: require; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.require (environment, resource_set_dependent, resource_id_dependent, resource_id_dependency) FROM stdin;
af711d09-06cb-434a-881b-27af6dc765b0	4081727f-5e23-4927-9570-401bae668c57	fs::File[localhost,path=/tmp/test]	std::AgentConfig[internal,agentname=localhost]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958	test::Resource[agent1,key=key3]	test::Fail[agent1,key=key2]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958	test::Resource[agent1,key=key5]	test::Resource[agent1,key=key4]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	fc6e0ef7-d166-4561-be74-79e8a8a66d94	test::Resource[agent1,key=key3]	test::Fail[agent1,key=key2]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	fc6e0ef7-d166-4561-be74-79e8a8a66d94	test::Resource[agent1,key=key5]	test::Resource[agent1,key=key4]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d	test::Resource[agent1,key=key3]	test::Fail[agent1,key=key2]
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d	test::Resource[agent1,key=key5]	test::Resource[agent1,key=key4]
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	36a199b7-d8f3-4dfc-86e9-36324ee34a2a
af711d09-06cb-434a-881b-27af6dc765b0	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	4081727f-5e23-4927-9570-401bae668c57
af711d09-06cb-434a-881b-27af6dc765b0	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	4081727f-5e23-4927-9570-401bae668c57
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d7b703f3-9fb1-4c7c-b416-28b892df418f
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	2782fea8-afe9-4375-873b-87bb31f4ae20
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	2782fea8-afe9-4375-873b-87bb31f4ae20
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	c751e04a-9c2d-46f6-80c9-d1dceb365acc
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0fbe8d9c-d0e7-4d2e-a840-f5b7eed53a0a
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ba336abb-0e85-4f0c-9b6d-5ff7292818f1
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	16a02010-420b-41d0-9570-b5a985c881fa
60256208-0349-46ce-9b2c-1893dba2a05e	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	fa5b37ac-26c9-4837-9248-60b2312595fb
60256208-0349-46ce-9b2c-1893dba2a05e	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	d6d763dc-0b48-4d70-80ad-965d98f93791
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0e90d8e4-0d07-43f1-9170-1c3c89da528a
60256208-0349-46ce-9b2c-1893dba2a05e	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	b691635b-260a-44e8-8864-e0ac0333f50a
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
1dc4bd5e-2d74-488a-a9f3-55f71a093132	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-11-10 15:57:00.691376+01
f6ee9dd5-f6b0-4e34-9db6-f45d6c2d0065	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-11-10 15:57:00.699115+01
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-11-10 15:57:00.540687+01	\N	\N	\N
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test]	2026-11-10 15:56:36.397263+01	\N	2026-11-10 15:56:36.397263+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:56:36.387628+01	f	\N	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Fail[agent1,key=key2]	2026-11-10 15:57:00.548814+01	\N	2026-11-10 15:57:00.548814+01	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:57:00.540687+01	f	\N	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key10]	2026-11-10 15:57:00.699115+01	\N	2026-11-10 15:57:00.699115+01	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.675526+01	f	f6ee9dd5-f6b0-4e34-9db6-f45d6c2d0065	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key3]	2026-11-10 15:57:00.551331+01	\N	2026-11-10 15:57:00.551331+01	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-11-10 15:57:00.540687+01	f	\N	\N
af711d09-06cb-434a-881b-27af6dc765b0	std::AgentConfig[internal,agentname=localhost]	2026-11-10 15:56:46.041061+01	\N	2026-11-10 15:56:46.041061+01	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:56:46.032328+01	f	\N	\N
af711d09-06cb-434a-881b-27af6dc765b0	fs::File[localhost,path=/tmp/test]	2026-11-10 15:56:46.047348+01	\N	2026-11-10 15:56:46.047348+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:56:46.032328+01	f	\N	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key1]	2026-11-10 15:57:00.556178+01	2026-11-10 15:57:00.552067+01	2026-11-10 15:57:00.556178+01	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.540687+01	t	\N	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key9]	2026-11-10 15:57:00.70553+01	2026-11-10 15:57:00.700992+01	2026-11-10 15:57:00.70553+01	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.675526+01	t	\N	\N
60256208-0349-46ce-9b2c-1893dba2a05e	fs::File[localhost,path=/tmp/test_orphan]	2026-11-10 15:56:48.350347+01	\N	2026-11-10 15:56:48.350347+01	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:56:48.34372+01	f	\N	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key7]	2026-11-10 15:57:00.710761+01	2026-11-10 15:57:00.706782+01	2026-11-10 15:57:00.710761+01	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.675526+01	t	\N	\N
60256208-0349-46ce-9b2c-1893dba2a05e	test::Resource[agent2,key=key2]	2026-11-10 15:57:00.221171+01	\N	2026-11-10 15:57:00.221171+01	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:57:00.20178+01	f	\N	\N
60256208-0349-46ce-9b2c-1893dba2a05e	test::Resource[agent3,key=key3]	2026-11-10 15:57:00.210419+01	\N	2026-11-10 15:57:00.210419+01	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-11-10 15:57:00.20178+01	f	\N	7
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-11-10 15:57:00.540687+01	\N	\N	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key6]	2026-11-10 15:57:00.560636+01	2026-11-10 15:57:00.557036+01	2026-11-10 15:57:00.560636+01	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.540687+01	t	\N	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	test::Resource[agent1,key=key11]	2026-11-10 15:57:00.691376+01	\N	2026-11-10 15:57:00.691376+01	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-10 15:57:00.675526+01	f	1dc4bd5e-2d74-488a-a9f3-55f71a093132	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	36a199b7-d8f3-4dfc-86e9-36324ee34a2a	\N
af711d09-06cb-434a-881b-27af6dc765b0	4081727f-5e23-4927-9570-401bae668c57	\N
60256208-0349-46ce-9b2c-1893dba2a05e	d7b703f3-9fb1-4c7c-b416-28b892df418f	\N
60256208-0349-46ce-9b2c-1893dba2a05e	2782fea8-afe9-4375-873b-87bb31f4ae20	\N
60256208-0349-46ce-9b2c-1893dba2a05e	c751e04a-9c2d-46f6-80c9-d1dceb365acc	\N
60256208-0349-46ce-9b2c-1893dba2a05e	0fbe8d9c-d0e7-4d2e-a840-f5b7eed53a0a	\N
60256208-0349-46ce-9b2c-1893dba2a05e	ba336abb-0e85-4f0c-9b6d-5ff7292818f1	\N
60256208-0349-46ce-9b2c-1893dba2a05e	16a02010-420b-41d0-9570-b5a985c881fa	\N
60256208-0349-46ce-9b2c-1893dba2a05e	fa5b37ac-26c9-4837-9248-60b2312595fb	set-a
60256208-0349-46ce-9b2c-1893dba2a05e	d6d763dc-0b48-4d70-80ad-965d98f93791	set-b
60256208-0349-46ce-9b2c-1893dba2a05e	0e90d8e4-0d07-43f1-9170-1c3c89da528a	\N
60256208-0349-46ce-9b2c-1893dba2a05e	b691635b-260a-44e8-8864-e0ac0333f50a	set-a
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	fc6e0ef7-d166-4561-be74-79e8a8a66d94	\N
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	1	36a199b7-d8f3-4dfc-86e9-36324ee34a2a
af711d09-06cb-434a-881b-27af6dc765b0	1	4081727f-5e23-4927-9570-401bae668c57
60256208-0349-46ce-9b2c-1893dba2a05e	2	d7b703f3-9fb1-4c7c-b416-28b892df418f
60256208-0349-46ce-9b2c-1893dba2a05e	3	2782fea8-afe9-4375-873b-87bb31f4ae20
60256208-0349-46ce-9b2c-1893dba2a05e	4	c751e04a-9c2d-46f6-80c9-d1dceb365acc
60256208-0349-46ce-9b2c-1893dba2a05e	5	0fbe8d9c-d0e7-4d2e-a840-f5b7eed53a0a
60256208-0349-46ce-9b2c-1893dba2a05e	6	ba336abb-0e85-4f0c-9b6d-5ff7292818f1
60256208-0349-46ce-9b2c-1893dba2a05e	7	16a02010-420b-41d0-9570-b5a985c881fa
60256208-0349-46ce-9b2c-1893dba2a05e	7	fa5b37ac-26c9-4837-9248-60b2312595fb
60256208-0349-46ce-9b2c-1893dba2a05e	7	d6d763dc-0b48-4d70-80ad-965d98f93791
60256208-0349-46ce-9b2c-1893dba2a05e	8	0e90d8e4-0d07-43f1-9170-1c3c89da528a
60256208-0349-46ce-9b2c-1893dba2a05e	8	b691635b-260a-44e8-8864-e0ac0333f50a
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	824cf86c-5c34-4c5a-99f9-6f3eb8ffb958
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	fc6e0ef7-d166-4561-be74-79e8a8a66d94
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	3	7a45e5b0-7dab-47d9-b22c-3eac2c0a014d
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
63522347-0cce-4261-80b7-2467b5531939	store	2026-11-10 15:56:36.336497+01	2026-11-10 15:56:36.343098+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T15:56:36.343110+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	1	{"fs::File[localhost,path=/tmp/test],v=1"}
fa5269f5-f0ab-4a48-b349-2b0be7785d2f	deploy	2026-11-10 15:56:36.395099+01	2026-11-10 15:56:36.397263+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:56:36.396381+01:00\\"}"}	unavailable	\N	nochange	60256208-0349-46ce-9b2c-1893dba2a05e	1	{"fs::File[localhost,path=/tmp/test],v=1"}
66bbe605-23bc-4daf-8f7b-b17a00c1b262	store	2026-11-10 15:56:45.929011+01	2026-11-10 15:56:45.937706+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T15:56:45.937718+01:00\\"}"}	\N	\N	\N	af711d09-06cb-434a-881b-27af6dc765b0	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
00cccb12-4777-44c1-b139-afaa9c4f8f82	deploy	2026-11-10 15:56:46.038724+01	2026-11-10 15:56:46.041061+01	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:56:46.040519+01:00\\"}"}	unavailable	\N	nochange	af711d09-06cb-434a-881b-27af6dc765b0	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
7614ade4-88d3-4d33-ae9f-16d2913893c2	deploy	2026-11-10 15:56:46.046117+01	2026-11-10 15:56:46.047348+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:56:46.046905+01:00\\"}"}	unavailable	\N	nochange	af711d09-06cb-434a-881b-27af6dc765b0	1	{"fs::File[localhost,path=/tmp/test],v=1"}
52cc99f6-c14f-4ff9-abc8-a9b6ea9f1388	store	2026-11-10 15:56:47.128276+01	2026-11-10 15:56:47.130711+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-10T15:56:47.130720+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	2	{"fs::File[localhost,path=/tmp/test],v=2"}
de84456b-06be-435b-a15a-6827d02379c0	store	2026-11-10 15:56:48.225579+01	2026-11-10 15:56:48.232336+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-10T15:56:48.232350+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
10413e4f-86ac-4a69-916d-8796ceb93c96	deploy	2026-11-10 15:56:48.347631+01	2026-11-10 15:56:48.350347+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-11-10T15:56:48.349826+01:00\\"}"}	unavailable	\N	nochange	60256208-0349-46ce-9b2c-1893dba2a05e	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
3a34777a-16df-443c-8848-c41a7e3e0ca5	store	2026-11-10 15:56:49.44197+01	2026-11-10 15:56:49.444418+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-11-10T15:56:49.444427+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	4	{"fs::File[localhost,path=/tmp/test],v=4"}
db940d3b-a109-49df-8dad-6360ac40b3dc	store	2026-11-10 15:56:50.566793+01	2026-11-10 15:56:50.569447+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-11-10T15:56:50.569456+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	5	{"fs::File[localhost,path=/tmp/test],v=5"}
b061a1d9-25be-4533-9fab-ca1fc76d33fc	store	2026-11-10 15:57:00.123883+01	2026-11-10 15:57:00.126003+01	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-11-10T15:57:00.126012+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	6	{"fs::File[localhost,path=/tmp/test],v=6"}
ecbd2dff-88fe-4788-a72c-26364acdd540	store	2026-11-10 15:57:00.172074+01	2026-11-10 15:57:00.17629+01	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-11-10T15:57:00.176298+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	7	{"test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7"}
05c5c5f6-d9da-45dc-ae89-0f01d762bbfc	deploy	2026-11-10 15:57:00.208304+01	2026-11-10 15:57:00.210419+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.209734+01:00\\"}"}	unavailable	\N	nochange	60256208-0349-46ce-9b2c-1893dba2a05e	7	{"test::Resource[agent3,key=key3],v=7"}
fb74d0fc-fd4c-458e-b653-8d099bcfdea4	deploy	2026-11-10 15:57:00.212022+01	2026-11-10 15:57:00.221171+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.220656+01:00\\"}"}	unavailable	\N	nochange	60256208-0349-46ce-9b2c-1893dba2a05e	7	{"test::Resource[agent2,key=key2],v=7"}
9e939e8f-2d08-4c35-80ac-cc93330ff06c	store	2026-11-10 15:57:00.343083+01	2026-11-10 15:57:00.364538+01	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-11-10T15:57:00.364556+01:00\\"}"}	\N	\N	\N	60256208-0349-46ce-9b2c-1893dba2a05e	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	store	2026-11-10 15:57:00.53591+01	2026-11-10 15:57:00.53844+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-10T15:57:00.538448+01:00\\"}"}	\N	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1"}
d067127e-7a6c-4b3d-8abf-37b73b8f9e98	deploy	2026-11-10 15:57:00.545581+01	2026-11-10 15:57:00.548814+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d238ca8f-6f4d-43a5-ba93-7c2b9f2fa63b).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"d238ca8f-6f4d-43a5-ba93-7c2b9f2fa63b\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.546630+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/tests/conftest.py\\\\\\", line 2601, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.548079+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: d238ca8f-6f4d-43a5-ba93-7c2b9f2fa63b) - duration: 0.0021 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0020933151245117188, \\"deploy_id\\": \\"d238ca8f-6f4d-43a5-ba93-7c2b9f2fa63b\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.548777+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Fail[agent1,key=key2],v=1"}
d1d06575-e091-4d23-a299-4488b5120d7e	deploy	2026-11-10 15:57:00.550208+01	2026-11-10 15:57:00.551331+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: fce5fb10-c26b-48b5-b814-84549dd58cce).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"fce5fb10-c26b-48b5-b814-84549dd58cce\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.550842+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.551099+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: fce5fb10-c26b-48b5-b814-84549dd58cce) - duration: 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0004227161407470703, \\"deploy_id\\": \\"fce5fb10-c26b-48b5-b814-84549dd58cce\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.551302+01:00\\"}"}	skipped	\N	nochange	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key3],v=1"}
3ad22fbd-50d9-4c43-8728-1791adeb074c	deploy	2026-11-10 15:57:00.552093+01	2026-11-10 15:57:00.556178+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: c32b0b2b-8aa4-454e-88b3-1c788b201b48).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"c32b0b2b-8aa4-454e-88b3-1c788b201b48\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.552712+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: c32b0b2b-8aa4-454e-88b3-1c788b201b48) - duration: 0.0034 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0033926963806152344, \\"deploy_id\\": \\"c32b0b2b-8aa4-454e-88b3-1c788b201b48\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.556147+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key1],v=1"}
ba6b27f1-8a76-42db-a5ca-d52287328d95	deploy	2026-11-10 15:57:00.557062+01	2026-11-10 15:57:00.560636+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: e5a48519-730d-41d1-8136-51392a76fc40).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"e5a48519-730d-41d1-8136-51392a76fc40\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.557674+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: e5a48519-730d-41d1-8136-51392a76fc40) - duration: 0.0029 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.002888202667236328, \\"deploy_id\\": \\"e5a48519-730d-41d1-8136-51392a76fc40\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.560608+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key6],v=1"}
c70a9b97-67d3-48fd-a7f8-1c84725008bf	store	2026-11-10 15:57:00.668119+01	2026-11-10 15:57:00.671379+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-10T15:57:00.671386+01:00\\"}"}	\N	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	{"test::Resource[agent1,key=key10],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key3],v=2"}
57536331-6d1c-4c06-89be-0b054cf487dc	dryrun	2026-11-10 15:57:00.67582+01	2026-11-10 15:57:00.676191+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.675876+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002455711364746094, \\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.676168+01:00\\"}"}	dry	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key5],v=1"}
410d714c-efe0-4ec5-a620-fa83ce8e5892	dryrun	2026-11-10 15:57:00.663387+01	2026-11-10 15:57:00.663799+01	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.663452+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00026917457580566406, \\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.663780+01:00\\"}"}	dry	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Fail[agent1,key=key2],v=1"}
1c5f881b-b1d3-48f6-8559-74984892b468	dryrun	2026-11-10 15:57:00.668869+01	2026-11-10 15:57:00.669298+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.668925+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00031447410583496094, \\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.669284+01:00\\"}"}	dry	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key1],v=1"}
777bc73c-8845-472e-9fa0-c0bcb595695e	dryrun	2026-11-10 15:57:00.671965+01	2026-11-10 15:57:00.672429+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.672019+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00034999847412109375, \\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.672414+01:00\\"}"}	dry	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key3],v=1"}
2076d81d-b891-47ba-aa3d-75076f7dc95b	deploy	2026-11-10 15:57:00.683123+01	2026-11-10 15:57:00.691376+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 5abc6e45-9e32-4320-a07d-8788cd4d2047).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"5abc6e45-9e32-4320-a07d-8788cd4d2047\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.684465+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.684800+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 5abc6e45-9e32-4320-a07d-8788cd4d2047) - duration: 0.0068 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.006781816482543945, \\"deploy_id\\": \\"5abc6e45-9e32-4320-a07d-8788cd4d2047\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.691318+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	{"test::Resource[agent1,key=key11],v=2"}
d15403bd-d3d5-408f-b146-fa13bdf53e54	deploy	2026-11-10 15:57:00.693821+01	2026-11-10 15:57:00.699115+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 88201183-9220-4153-a6ee-09146b9de2f9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"88201183-9220-4153-a6ee-09146b9de2f9\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.694999+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.695361+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 88201183-9220-4153-a6ee-09146b9de2f9) - duration: 0.0040 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0040225982666015625, \\"deploy_id\\": \\"88201183-9220-4153-a6ee-09146b9de2f9\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.699077+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	{"test::Resource[agent1,key=key10],v=2"}
f6e46f13-e69e-478b-b8c9-6a773677d13c	deploy	2026-11-10 15:57:00.701033+01	2026-11-10 15:57:00.70553+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2b76e83b-0969-4cf7-a16e-d0e37f2c72ba).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"2b76e83b-0969-4cf7-a16e-d0e37f2c72ba\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.701909+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 2b76e83b-0969-4cf7-a16e-d0e37f2c72ba) - duration: 0.0035 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.003534078598022461, \\"deploy_id\\": \\"2b76e83b-0969-4cf7-a16e-d0e37f2c72ba\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.705491+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	{"test::Resource[agent1,key=key9],v=2"}
1207c00f-adee-43a6-9f1e-933ff8a77840	deploy	2026-11-10 15:57:00.706817+01	2026-11-10 15:57:00.710761+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: eaa4d9cf-fbc2-4463-81e5-35bafefa0f6a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"eaa4d9cf-fbc2-4463-81e5-35bafefa0f6a\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.707710+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: eaa4d9cf-fbc2-4463-81e5-35bafefa0f6a) - duration: 0.0030 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0029592514038085938, \\"deploy_id\\": \\"eaa4d9cf-fbc2-4463-81e5-35bafefa0f6a\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.710723+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2	{"test::Resource[agent1,key=key7],v=2"}
06bc74e4-90a9-4033-8751-9c6dda22850d	dryrun	2026-11-10 15:57:00.711894+01	2026-11-10 15:57:00.712174+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.711942+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: cd4031af-969a-452f-b642-5db1d95235c1 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00017786026000976562, \\"dry_run_id\\": \\"cd4031af-969a-452f-b642-5db1d95235c1\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-10T15:57:00.712161+01:00\\"}"}	dry	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1	{"test::Resource[agent1,key=key6],v=1"}
070e5a5e-8756-4f99-aa01-5f795262c3c9	store	2026-11-10 15:57:00.825581+01	2026-11-10 15:57:00.828154+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-10T15:57:00.828163+01:00\\"}"}	\N	\N	\N	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	3	{"test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key4],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
60256208-0349-46ce-9b2c-1893dba2a05e	63522347-0cce-4261-80b7-2467b5531939	fs::File[localhost,path=/tmp/test]	1
60256208-0349-46ce-9b2c-1893dba2a05e	fa5269f5-f0ab-4a48-b349-2b0be7785d2f	fs::File[localhost,path=/tmp/test]	1
af711d09-06cb-434a-881b-27af6dc765b0	66bbe605-23bc-4daf-8f7b-b17a00c1b262	fs::File[localhost,path=/tmp/test]	1
af711d09-06cb-434a-881b-27af6dc765b0	66bbe605-23bc-4daf-8f7b-b17a00c1b262	std::AgentConfig[internal,agentname=localhost]	1
af711d09-06cb-434a-881b-27af6dc765b0	00cccb12-4777-44c1-b139-afaa9c4f8f82	std::AgentConfig[internal,agentname=localhost]	1
af711d09-06cb-434a-881b-27af6dc765b0	7614ade4-88d3-4d33-ae9f-16d2913893c2	fs::File[localhost,path=/tmp/test]	1
60256208-0349-46ce-9b2c-1893dba2a05e	52cc99f6-c14f-4ff9-abc8-a9b6ea9f1388	fs::File[localhost,path=/tmp/test]	2
60256208-0349-46ce-9b2c-1893dba2a05e	de84456b-06be-435b-a15a-6827d02379c0	fs::File[localhost,path=/tmp/test]	3
60256208-0349-46ce-9b2c-1893dba2a05e	de84456b-06be-435b-a15a-6827d02379c0	fs::File[localhost,path=/tmp/test_orphan]	3
60256208-0349-46ce-9b2c-1893dba2a05e	10413e4f-86ac-4a69-916d-8796ceb93c96	fs::File[localhost,path=/tmp/test_orphan]	3
60256208-0349-46ce-9b2c-1893dba2a05e	3a34777a-16df-443c-8848-c41a7e3e0ca5	fs::File[localhost,path=/tmp/test]	4
60256208-0349-46ce-9b2c-1893dba2a05e	db940d3b-a109-49df-8dad-6360ac40b3dc	fs::File[localhost,path=/tmp/test]	5
60256208-0349-46ce-9b2c-1893dba2a05e	b061a1d9-25be-4533-9fab-ca1fc76d33fc	fs::File[localhost,path=/tmp/test]	6
60256208-0349-46ce-9b2c-1893dba2a05e	ecbd2dff-88fe-4788-a72c-26364acdd540	test::Resource[agent3,key=key3]	7
60256208-0349-46ce-9b2c-1893dba2a05e	ecbd2dff-88fe-4788-a72c-26364acdd540	fs::File[localhost,path=/tmp/test]	7
60256208-0349-46ce-9b2c-1893dba2a05e	ecbd2dff-88fe-4788-a72c-26364acdd540	test::Resource[agent2,key=key2]	7
60256208-0349-46ce-9b2c-1893dba2a05e	05c5c5f6-d9da-45dc-ae89-0f01d762bbfc	test::Resource[agent3,key=key3]	7
60256208-0349-46ce-9b2c-1893dba2a05e	fb74d0fc-fd4c-458e-b653-8d099bcfdea4	test::Resource[agent2,key=key2]	7
60256208-0349-46ce-9b2c-1893dba2a05e	9e939e8f-2d08-4c35-80ac-cc93330ff06c	test::Resource[agent2,key=key2]	8
60256208-0349-46ce-9b2c-1893dba2a05e	9e939e8f-2d08-4c35-80ac-cc93330ff06c	fs::File[localhost,path=/tmp/test]	8
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Fail[agent1,key=key2]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Resource[agent1,key=key5]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Resource[agent1,key=key4]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Resource[agent1,key=key3]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Resource[agent1,key=key1]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	081ac2f6-e8d1-41fb-8076-eeb9c93dcdd2	test::Resource[agent1,key=key6]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	d067127e-7a6c-4b3d-8abf-37b73b8f9e98	test::Fail[agent1,key=key2]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	d1d06575-e091-4d23-a299-4488b5120d7e	test::Resource[agent1,key=key3]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	3ad22fbd-50d9-4c43-8728-1791adeb074c	test::Resource[agent1,key=key1]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	ba6b27f1-8a76-42db-a5ca-d52287328d95	test::Resource[agent1,key=key6]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	410d714c-efe0-4ec5-a620-fa83ce8e5892	test::Fail[agent1,key=key2]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1c5f881b-b1d3-48f6-8559-74984892b468	test::Resource[agent1,key=key1]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key10]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Fail[agent1,key=key2]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key1]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key9]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key7]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key11]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key5]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key4]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	c70a9b97-67d3-48fd-a7f8-1c84725008bf	test::Resource[agent1,key=key3]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	777bc73c-8845-472e-9fa0-c0bcb595695e	test::Resource[agent1,key=key3]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	57536331-6d1c-4c06-89be-0b054cf487dc	test::Resource[agent1,key=key5]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2076d81d-b891-47ba-aa3d-75076f7dc95b	test::Resource[agent1,key=key11]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	d15403bd-d3d5-408f-b146-fa13bdf53e54	test::Resource[agent1,key=key10]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	f6e46f13-e69e-478b-b8c9-6a773677d13c	test::Resource[agent1,key=key9]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	1207c00f-adee-43a6-9f1e-933ff8a77840	test::Resource[agent1,key=key7]	2
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	06bc74e4-90a9-4033-8751-9c6dda22850d	test::Resource[agent1,key=key6]	1
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key5]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key8]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key3]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Fail[agent1,key=key2]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key7]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key1]	3
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	070e5a5e-8756-4f99-aa01-5f795262c3c9	test::Resource[agent1,key=key4]	3
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
af711d09-06cb-434a-881b-27af6dc765b0	1
60256208-0349-46ce-9b2c-1893dba2a05e	8
fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	60256208-0349-46ce-9b2c-1893dba2a05e	2026-11-10 15:56:25.592313+01	\N	ebc2a991-dabf-4071-ae5c-423907d4b7f1
arnaud-inmanta-laptop	af711d09-06cb-434a-881b-27af6dc765b0	2026-11-10 15:56:25.70581+01	\N	af46e25a-483e-4477-98ce-6a7b75c2c320
arnaud-inmanta-laptop	fd1f1e9c-5b25-433c-9aba-0d50b96c5313	2026-11-10 15:57:00.404319+01	2026-11-10 15:57:00.817662+01	2725db24-42e6-4a9e-90be-99314d4f3898
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610161,202610280,202611100}
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
-- Name: require require_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.require
    ADD CONSTRAINT require_pkey PRIMARY KEY (environment, resource_set_dependent, resource_id_dependent, resource_id_dependency);


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
-- Name: require_environment_resource_id_dependency_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX require_environment_resource_id_dependency_index ON public.require USING btree (environment, resource_id_dependency);


--
-- Name: require_environment_resource_id_dependent_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX require_environment_resource_id_dependent_index ON public.require USING btree (environment, resource_id_dependent);


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
-- Name: require require_resource_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.require
    ADD CONSTRAINT require_resource_fkey FOREIGN KEY (environment, resource_set_dependent, resource_id_dependent) REFERENCES public.resource(environment, resource_set, resource_id) ON DELETE CASCADE;


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

--\unrestrict u8w6bOGy2z8zHLFBZn5YHe5Z4CKkaWYRFf3SW6PrCQEfebuSzIWbj8Zqk84O3yR

