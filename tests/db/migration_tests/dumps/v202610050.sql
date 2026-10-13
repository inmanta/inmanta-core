--
-- PostgreSQL database dump
--

--\restrict SnUAYhTznxDEiGTdqmukMCexBbUo6feDAiigIL3wEdVDBMq3bXJRjUsbn0bhiWD

-- Dumped from database version 16.13 (Debian 16.13-1.pgdg13+1)
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
    resources jsonb DEFAULT '{}'::jsonb,
    resource_filter jsonb
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
ba8f758f-810f-469e-a498-80c54b1efa88	$__scheduler	f	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	$__scheduler	f	\N
e3c8e275-af11-4dbc-bc43-0aad1ee5b602	$__scheduler	f	\N
ba8f758f-810f-469e-a498-80c54b1efa88	internal	f	\N
ba8f758f-810f-469e-a498-80c54b1efa88	localhost	f	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	internal	f	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	localhost	f	\N
ba8f758f-810f-469e-a498-80c54b1efa88	agent3	f	\N
ba8f758f-810f-469e-a498-80c54b1efa88	agent2	f	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	agent1	t	t
91bb17b7-b5dd-405a-a8e2-861710c241f8	$__scheduler	t	t
b3aa1307-d47c-4df8-9b63-92b21f0a202d	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
1	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
1	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
1	internal	std	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5
1	localhost	fs	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5
2	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
2	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
2	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
3	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
3	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
3	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
4	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
4	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
4	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
5	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
5	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
5	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
6	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
6	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
6	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
7	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
7	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
7	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
8	localhost	fs	ba8f758f-810f-469e-a498-80c54b1efa88
8	internal	std	ba8f758f-810f-469e-a498-80c54b1efa88
8	localhost	std	ba8f758f-810f-469e-a498-80c54b1efa88
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
df4ceae0-da90-4705-83c9-d0a9c162cdd6	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:22.056939+00	2026-10-05 11:42:28.822768+00	2026-10-05 11:42:22.025766+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	341d91cb-4247-4a33-a6bd-e315d1ad23f3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
aa618bd9-f657-4ef6-be5a-e76b8119b63e	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	2026-10-05 11:42:29.043161+00	2026-10-05 11:42:34.427541+00	2026-10-05 11:42:29.023492+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	81009e86-8523-4ed2-abfb-b26d076fcffc	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
e6b8e687-95e4-4eb4-ada2-8253d105b931	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:34.710296+00	2026-10-05 11:42:35.88837+00	2026-10-05 11:42:34.681782+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	c1a91a14-03a7-49a3-a127-930696bdab87	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
9fd78720-c29e-4723-baee-76072dd50f31	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:36.012913+00	2026-10-05 11:42:37.225554+00	2026-10-05 11:42:36.000125+00	{}	{"add_one_resource": "true"}	t	f	t	3	05e83cfa-6f3d-4dd5-a0a1-c4fc56c91ce3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
04df4b17-b691-4064-a13f-e0975eeb8b20	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:37.475864+00	2026-10-05 11:42:38.582419+00	2026-10-05 11:42:37.455893+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	85e99b59-d795-4f89-9abf-cd118c023fae	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
1ff56ad2-6795-4805-a49a-e169b895f2ab	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:38.815984+00	2026-10-05 11:42:39.932627+00	2026-10-05 11:42:38.793857+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	138585b9-dc21-4f44-970e-62cddafbd139	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
cfceb396-2cd9-44e6-8bea-7c8469b11af2	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:40.043367+00	2026-10-05 11:42:44.387982+00	2026-10-05 11:42:40.03029+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	328eeefd-4770-4dc5-ad36-66019dbad5d0	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
ef54d521-0d8e-4e9b-9e6b-6bbed00098be	b3aa1307-d47c-4df8-9b63-92b21f0a202d	2026-10-05 11:42:45.888162+00	2026-10-05 11:42:45.925937+00	2026-10-05 11:42:45.838433+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	20a49720-e0b3-43a9-8b41-0eaba8d0ffc6	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:28.760038+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	91bb17b7-b5dd-405a-a8e2-861710c241f8	2026-10-05 11:42:44.98264+00	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
1	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	2026-10-05 11:42:34.359699+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:35.829786+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:37.164643+00	t	{"export_metadata": {"type": "manual", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:38.521932+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:39.876143+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:44.334503+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
2	91bb17b7-b5dd-405a-a8e2-861710c241f8	2026-10-05 11:42:45.302822+00	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:44.542254+00	t	\N	4	{}	{}	6	t	\N	\N
8	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:44.726217+00	t	\N	3	{}	{}	7	t	\N	\N
3	91bb17b7-b5dd-405a-a8e2-861710c241f8	2026-10-05 11:42:45.61838+00	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	1	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	1	fs	1.2.0
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	std	7.0.0
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	2	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	2	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	3	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	3	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	4	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	4	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	5	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	5	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	6	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	6	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	7	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	7	std	8.7.4
ba8f758f-810f-469e-a498-80c54b1efa88	8	fs	1.2.0
ba8f758f-810f-469e-a498-80c54b1efa88	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	discovery::Discovered[myagent,name=discovered]	{}	2026-10-05 11:42:45.651312+00	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
ba8f758f-810f-469e-a498-80c54b1efa88	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-05 11:42:45.651345+00	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter) FROM stdin;
edfd45cd-b3dd-471d-a7d9-7c9ef876f311	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	2026-10-05 11:42:45.247127+00	6	0	{"1c125915-952b-5d5f-9419-47d8934202bc": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "22333aa5-1f0b-56c8-a6da-d59bb0f78b3e": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "261901dd-40fa-566f-ba01-17ef18be8f9f": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "9cc87cea-5bab-55a8-b9e9-4f079c25f7b7": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "b9799b36-bd14-5737-a879-cc089ccf49f4": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "c83728ae-eb30-5b17-bb57-10d108d63e7f": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
b3aa1307-d47c-4df8-9b63-92b21f0a202d	dev-4	431a1b53-dc13-4fe3-82eb-7dc3e75d7649			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
ba8f758f-810f-469e-a498-80c54b1efa88	dev-1	431a1b53-dc13-4fe3-82eb-7dc3e75d7649			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	dev-1-twin	431a1b53-dc13-4fe3-82eb-7dc3e75d7649			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
e3c8e275-af11-4dbc-bc43-0aad1ee5b602	dev-2	431a1b53-dc13-4fe3-82eb-7dc3e75d7649			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
91bb17b7-b5dd-405a-a8e2-861710c241f8	dev-3	431a1b53-dc13-4fe3-82eb-7dc3e75d7649			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.4	ba8f758f-810f-469e-a498-80c54b1efa88	\N	f
fs	1.2.0	ba8f758f-810f-469e-a498-80c54b1efa88	\N	f
std	7.0.0	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	\N	f
fs	1.2.0	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	\N	f
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
6a9d0521-fbff-41a1-816d-4cd1072a9fa9	b3aa1307-d47c-4df8-9b63-92b21f0a202d	2026-10-05 11:42:45.938907+00	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/ef54d521-0d8e-4e9b-9e6b-6bbed00098be	f	f	ef54d521-0d8e-4e9b-9e6b-6bbed00098be
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
b8e6b265-9924-48b5-8392-9ea5b3807901	fact1	value1	ba8f758f-810f-469e-a498-80c54b1efa88	std::testing::NullResource[localhost,name=test1]	fact	2026-10-05 11:42:38.694505+00	{}	f
8cd39ef5-4280-4f2b-a51c-d814fce2f236	fact2	value2	ba8f758f-810f-469e-a498-80c54b1efa88	std::testing::NullResource[localhost,name=test2]	fact	2026-10-05 11:42:38.719014+00	{}	t
66fa673c-b66a-4060-a948-9f1a60693218	fact3	value3	ba8f758f-810f-469e-a498-80c54b1efa88	std::testing::NullResource[localhost,name=test3]	fact	2026-10-05 11:42:38.739806+00	{}	t
952d4c73-8c81-4cd6-a0d4-254e68409443	parameter1	value1	ba8f758f-810f-469e-a498-80c54b1efa88		fact	2026-10-05 11:42:38.752734+00	{}	f
6ea348fc-03f6-41e7-8db6-dc5cd8cc7731	parameter2	value2	ba8f758f-810f-469e-a498-80c54b1efa88		fact	2026-10-05 11:42:38.766287+00	{}	f
d01645a5-8f95-423b-ab3d-c85e1c77b442	parameter3	value3	ba8f758f-810f-469e-a498-80c54b1efa88		fact	2026-10-05 11:42:38.780746+00	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
431a1b53-dc13-4fe3-82eb-7dc3e75d7649	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
ba3c4c3d-4537-4246-aaa5-0cd7e2366243	2026-10-05 11:42:22.063973+00	2026-10-05 11:42:22.082432+00		Init		Using extra environment variables during compile \n	0	df4ceae0-da90-4705-83c9-d0a9c162cdd6
55f7a504-ca92-4517-97e3-c8fdb963de3b	2026-10-05 11:42:22.090257+00	2026-10-05 11:42:22.111153+00		Venv check		Creating new venv at /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env-py3.14\n	0	df4ceae0-da90-4705-83c9-d0a9c162cdd6
28728f88-3967-4402-b956-b9589cc38899	2026-10-05 11:42:22.123574+00	2026-10-05 11:42:22.487616+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	df4ceae0-da90-4705-83c9-d0a9c162cdd6
41f12c2c-5cda-4091-afdb-9e30bb454fd5	2026-10-05 11:42:29.079017+00	2026-10-05 11:42:29.099017+00		Venv check		Creating new venv at /tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env-py3.14\n	0	aa618bd9-f657-4ef6-be5a-e76b8119b63e
cd259038-1ef4-4ad8-9884-36520077c4bb	2026-10-05 11:42:38.857402+00	2026-10-05 11:42:38.875167+00		Venv check		Found existing venv\n	0	1ff56ad2-6795-4805-a49a-e169b895f2ab
a9e86dd0-aefa-4036-92a4-32e6de3f6e08	2026-10-05 11:42:29.111269+00	2026-10-05 11:42:29.342596+00	/tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	aa618bd9-f657-4ef6-be5a-e76b8119b63e
63103af8-02db-435c-be5f-836223340f83	2026-10-05 11:42:40.050454+00	2026-10-05 11:42:40.070646+00		Init		Using extra environment variables during compile \n	0	cfceb396-2cd9-44e6-8bea-7c8469b11af2
cfbb0f51-1aa3-41b6-8411-8bc9c78ec0ee	2026-10-05 11:42:27.725008+00	2026-10-05 11:42:28.815147+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpjbdty4wr --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.020 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.026 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.075 seconds\ncompiler       DEBUG   The entire export command took 0.146 seconds\n	0	df4ceae0-da90-4705-83c9-d0a9c162cdd6
b515feaf-f8f8-4985-916c-6fd2ae66b64e	2026-10-05 11:42:29.050104+00	2026-10-05 11:42:29.070885+00		Init		Using extra environment variables during compile \n	0	aa618bd9-f657-4ef6-be5a-e76b8119b63e
6bd0dcf3-809f-486e-8e69-b0fdeda5e29e	2026-10-05 11:42:40.078987+00	2026-10-05 11:42:40.095568+00		Venv check		Found existing venv\n	0	cfceb396-2cd9-44e6-8bea-7c8469b11af2
f366de25-a6cb-4304-a3cc-62b14463fb8c	2026-10-05 11:42:33.362096+00	2026-10-05 11:42:34.419428+00	/tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpbkjcxgsn --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.065 seconds\ncompiler       DEBUG   The entire export command took 0.132 seconds\n	0	aa618bd9-f657-4ef6-be5a-e76b8119b63e
cbcabf0a-adcf-473f-80f3-947553b3ca11	2026-10-05 11:42:38.823883+00	2026-10-05 11:42:38.848879+00		Init		Using extra environment variables during compile \n	0	1ff56ad2-6795-4805-a49a-e169b895f2ab
a2422453-4dc1-4c7d-b741-22a6e24d560d	2026-10-05 11:42:38.883586+00	2026-10-05 11:42:39.924022+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcpduezvk --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.033 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.039 seconds\ncompiler       DEBUG   The entire export command took 0.108 seconds\n	0	1ff56ad2-6795-4805-a49a-e169b895f2ab
2de83f1b-c2d0-41c5-88e4-4f2f6e068b03	2026-10-05 11:42:40.10797+00	2026-10-05 11:42:40.345108+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	cfceb396-2cd9-44e6-8bea-7c8469b11af2
864dae9c-c95d-4b69-984d-ecc1db39c308	2026-10-05 11:42:22.494404+00	2026-10-05 11:42:27.707795+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpqwdxm249:\n                                 Pip command: /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpqwdxm249 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.2)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.331.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.53-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Downloading sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.6/4.6 MB 25.7 MB/s  0:00:00\ninmanta.pip              DEBUG   Downloading inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: SQLAlchemy, mitogen, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.2\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.3 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	df4ceae0-da90-4705-83c9-d0a9c162cdd6
cbe92c94-b6ba-498e-a8ed-3f1db16ccc1a	2026-10-05 11:42:34.777019+00	2026-10-05 11:42:35.879292+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppcdiru7u --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.026 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.037 seconds\ncompiler       DEBUG   The entire export command took 0.101 seconds\n	0	e6b8e687-95e4-4eb4-ada2-8253d105b931
55de14b5-9878-429f-a273-94291458b4c7	2026-10-05 11:42:37.539294+00	2026-10-05 11:42:38.573671+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp2ck317db --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.036 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.055 seconds\ncompiler       DEBUG   The entire export command took 0.126 seconds\n	0	04df4b17-b691-4064-a13f-e0975eeb8b20
45590655-ad50-42b0-aa00-c1d35b63108a	2026-10-05 11:42:36.020216+00	2026-10-05 11:42:36.039339+00		Init		Using extra environment variables during compile add_one_resource='true'\n	0	9fd78720-c29e-4723-baee-76072dd50f31
c0ed7e6d-b7f5-4a3a-9f13-7edf9e054e1f	2026-10-05 11:42:36.072286+00	2026-10-05 11:42:37.218404+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpkosv9i7r --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.074 seconds\ncompiler       DEBUG   The entire export command took 0.148 seconds\n	0	9fd78720-c29e-4723-baee-76072dd50f31
a45446bf-73ec-48a5-93ce-61d5afddacb9	2026-10-05 11:42:36.047492+00	2026-10-05 11:42:36.064203+00		Venv check		Found existing venv\n	0	9fd78720-c29e-4723-baee-76072dd50f31
07ceb827-9d12-45f0-a825-fa5da84cabc3	2026-10-05 11:42:37.483078+00	2026-10-05 11:42:37.50357+00		Init		Using extra environment variables during compile \n	0	04df4b17-b691-4064-a13f-e0975eeb8b20
0164f5ce-6e3f-498a-8ceb-31a3c863cc0c	2026-10-05 11:42:29.350012+00	2026-10-05 11:42:33.354154+00	/tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpojpt_516:\n                                 Pip command: /tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpojpt_516 inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.2)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.331.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: SQLAlchemy, mitogen, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.2\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpavfhjp6p/server/5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.3 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	aa618bd9-f657-4ef6-be5a-e76b8119b63e
dd43cc9d-5e97-4b14-a9b5-476a8d3d8686	2026-10-05 11:42:37.512036+00	2026-10-05 11:42:37.529787+00		Venv check		Found existing venv\n	0	04df4b17-b691-4064-a13f-e0975eeb8b20
8e1fa0bd-4418-4aec-9e6b-bbe1f725644e	2026-10-05 11:42:34.718795+00	2026-10-05 11:42:34.739635+00		Init		Using extra environment variables during compile \n	0	e6b8e687-95e4-4eb4-ada2-8253d105b931
4aa2065a-0749-448a-a396-2ba713f0a2a2	2026-10-05 11:42:34.748291+00	2026-10-05 11:42:34.767515+00		Venv check		Found existing venv\n	0	e6b8e687-95e4-4eb4-ada2-8253d105b931
e69f4d24-22e1-4d06-a616-ebd599618f85	2026-10-05 11:42:43.357869+00	2026-10-05 11:42:44.378289+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ba8f758f-810f-469e-a498-80c54b1efa88 --server_address localhost --server_port 59651 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpsj5hrtig --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.026 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:59651/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:59651/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.041 seconds\ncompiler       DEBUG   The entire export command took 0.100 seconds\n	0	cfceb396-2cd9-44e6-8bea-7c8469b11af2
8fca8f1b-6028-495c-8878-6c6a418776ce	2026-10-05 11:42:40.352687+00	2026-10-05 11:42:43.340378+00	/tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpf9g4ryk3:\n                                 Pip command: /tmp/tmpavfhjp6p/server/ba8f758f-810f-469e-a498-80c54b1efa88/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpf9g4ryk3 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in ./.env/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.331.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/eb8f9ec9-f8a8-44ce-99f3-ec08609c2309/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	cfceb396-2cd9-44e6-8bea-7c8469b11af2
c8d3c186-da08-4a92-9543-af1d41d45f78	2026-10-05 11:42:45.895469+00	2026-10-05 11:42:45.91814+00		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpavfhjp6p/server/b3aa1307-d47c-4df8-9b63-92b21f0a202d/compiler and no repository set.\n	1	ef54d521-0d8e-4e9b-9e6b-6bbed00098be
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	fe4d4dfb-18ba-40b5-81a3-e32961b1857e
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	fe4d4dfb-18ba-40b5-81a3-e32961b1857e
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	07cd4f61-a37b-41ce-8fc9-259a9ba2fb7c
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	07cd4f61-a37b-41ce-8fc9-259a9ba2fb7c
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	58d81779-f32a-41f7-8582-8688dfa0a024
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	58d81779-f32a-41f7-8582-8688dfa0a024
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	e6a246b8-634f-484d-93b7-f7e426225edf
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e6a246b8-634f-484d-93b7-f7e426225edf
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	e6a246b8-634f-484d-93b7-f7e426225edf
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	23e3a4cf-0240-46f1-a42d-79646d0dc142
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	23e3a4cf-0240-46f1-a42d-79646d0dc142
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	b26676bf-79e9-42f6-8013-f078ac7d38ba
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b26676bf-79e9-42f6-8013-f078ac7d38ba
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	71d82e36-488d-4ad6-bfbf-0f0c7129409e
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	71d82e36-488d-4ad6-bfbf-0f0c7129409e
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	77947e40-0eca-4069-9b3f-6e5eaa69fb57
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	77947e40-0eca-4069-9b3f-6e5eaa69fb57
ba8f758f-810f-469e-a498-80c54b1efa88	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	b3f963ff-68be-4a1c-9b35-71f9f6359f56
ba8f758f-810f-469e-a498-80c54b1efa88	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	4d2cb211-f63d-4027-ae1c-a30b327b8e66
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ffe5fdf3-ed6f-4d3e-895b-83f1b8ee7220
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	ffe5fdf3-ed6f-4d3e-895b-83f1b8ee7220
ba8f758f-810f-469e-a498-80c54b1efa88	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	52a8dfd5-0604-4b92-b6fc-d418f62d74d8
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	4a7640f6-ae58-4759-8ed3-e86b5be0d792
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
414bdff4-4e3b-4a6e-9514-ef755b6475f8	91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-05 11:42:45.437226+00
b19f4eaf-d93c-411f-8170-7ad6eb96637f	91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-05 11:42:45.473715+00
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key7]	2026-10-05 11:42:45.395797+00	2026-10-05 11:42:45.367512+00	2026-10-05 11:42:45.395797+00	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:45.324792+00	t	\N	\N
ba8f758f-810f-469e-a498-80c54b1efa88	std::AgentConfig[internal,agentname=localhost]	2026-10-05 11:42:28.918688+00	\N	2026-10-05 11:42:28.918688+00	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:28.878488+00	f	\N	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-05 11:42:44.9996+00	\N	\N	\N
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test]	2026-10-05 11:42:28.942141+00	\N	2026-10-05 11:42:28.942141+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:28.878488+00	f	\N	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-05 11:42:44.9996+00	\N	\N	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key11]	2026-10-05 11:42:45.437226+00	\N	2026-10-05 11:42:45.437226+00	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:45.324792+00	f	414bdff4-4e3b-4a6e-9514-ef755b6475f8	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Fail[agent1,key=key2]	2026-10-05 11:42:45.036297+00	\N	2026-10-05 11:42:45.036297+00	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:44.9996+00	f	\N	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	std::AgentConfig[internal,agentname=localhost]	2026-10-05 11:42:34.574591+00	\N	2026-10-05 11:42:34.574591+00	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:34.537108+00	f	\N	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	fs::File[localhost,path=/tmp/test]	2026-10-05 11:42:34.609203+00	\N	2026-10-05 11:42:34.609203+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:34.537108+00	f	\N	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key10]	2026-10-05 11:42:45.473715+00	\N	2026-10-05 11:42:45.473715+00	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:45.324792+00	f	b19f4eaf-d93c-411f-8170-7ad6eb96637f	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key3]	2026-10-05 11:42:45.095001+00	\N	2026-10-05 11:42:45.095001+00	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-05 11:42:44.9996+00	f	\N	\N
ba8f758f-810f-469e-a498-80c54b1efa88	fs::File[localhost,path=/tmp/test_orphan]	2026-10-05 11:42:37.35417+00	\N	2026-10-05 11:42:37.35417+00	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:37.314645+00	f	\N	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key9]	2026-10-05 11:42:45.502464+00	2026-10-05 11:42:45.484821+00	2026-10-05 11:42:45.502464+00	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:45.324792+00	t	\N	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key1]	2026-10-05 11:42:45.132981+00	2026-10-05 11:42:45.10715+00	2026-10-05 11:42:45.132981+00	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:44.9996+00	t	\N	\N
ba8f758f-810f-469e-a498-80c54b1efa88	test::Resource[agent2,key=key2]	2026-10-05 11:42:44.608419+00	\N	2026-10-05 11:42:44.608419+00	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:44.580516+00	f	\N	\N
ba8f758f-810f-469e-a498-80c54b1efa88	test::Resource[agent3,key=key3]	2026-10-05 11:42:44.620329+00	\N	2026-10-05 11:42:44.620329+00	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-05 11:42:44.580516+00	f	\N	7
91bb17b7-b5dd-405a-a8e2-861710c241f8	test::Resource[agent1,key=key6]	2026-10-05 11:42:45.073053+00	2026-10-05 11:42:45.04876+00	2026-10-05 11:42:45.073053+00	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-05 11:42:44.9996+00	t	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	fe4d4dfb-18ba-40b5-81a3-e32961b1857e	\N
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	07cd4f61-a37b-41ce-8fc9-259a9ba2fb7c	\N
ba8f758f-810f-469e-a498-80c54b1efa88	58d81779-f32a-41f7-8582-8688dfa0a024	\N
ba8f758f-810f-469e-a498-80c54b1efa88	e6a246b8-634f-484d-93b7-f7e426225edf	\N
ba8f758f-810f-469e-a498-80c54b1efa88	23e3a4cf-0240-46f1-a42d-79646d0dc142	\N
ba8f758f-810f-469e-a498-80c54b1efa88	b26676bf-79e9-42f6-8013-f078ac7d38ba	\N
ba8f758f-810f-469e-a498-80c54b1efa88	71d82e36-488d-4ad6-bfbf-0f0c7129409e	\N
ba8f758f-810f-469e-a498-80c54b1efa88	77947e40-0eca-4069-9b3f-6e5eaa69fb57	\N
ba8f758f-810f-469e-a498-80c54b1efa88	b3f963ff-68be-4a1c-9b35-71f9f6359f56	set-a
ba8f758f-810f-469e-a498-80c54b1efa88	4d2cb211-f63d-4027-ae1c-a30b327b8e66	set-b
ba8f758f-810f-469e-a498-80c54b1efa88	ffe5fdf3-ed6f-4d3e-895b-83f1b8ee7220	\N
ba8f758f-810f-469e-a498-80c54b1efa88	52a8dfd5-0604-4b92-b6fc-d418f62d74d8	set-a
91bb17b7-b5dd-405a-a8e2-861710c241f8	807399bb-bb84-42c6-8598-9e306076e60b	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	5f895c44-08f4-4f64-97b1-527315c95fe2	\N
91bb17b7-b5dd-405a-a8e2-861710c241f8	4a7640f6-ae58-4759-8ed3-e86b5be0d792	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	1	fe4d4dfb-18ba-40b5-81a3-e32961b1857e
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	07cd4f61-a37b-41ce-8fc9-259a9ba2fb7c
ba8f758f-810f-469e-a498-80c54b1efa88	2	58d81779-f32a-41f7-8582-8688dfa0a024
ba8f758f-810f-469e-a498-80c54b1efa88	3	e6a246b8-634f-484d-93b7-f7e426225edf
ba8f758f-810f-469e-a498-80c54b1efa88	4	23e3a4cf-0240-46f1-a42d-79646d0dc142
ba8f758f-810f-469e-a498-80c54b1efa88	5	b26676bf-79e9-42f6-8013-f078ac7d38ba
ba8f758f-810f-469e-a498-80c54b1efa88	6	71d82e36-488d-4ad6-bfbf-0f0c7129409e
ba8f758f-810f-469e-a498-80c54b1efa88	7	77947e40-0eca-4069-9b3f-6e5eaa69fb57
ba8f758f-810f-469e-a498-80c54b1efa88	7	b3f963ff-68be-4a1c-9b35-71f9f6359f56
ba8f758f-810f-469e-a498-80c54b1efa88	7	4d2cb211-f63d-4027-ae1c-a30b327b8e66
ba8f758f-810f-469e-a498-80c54b1efa88	8	ffe5fdf3-ed6f-4d3e-895b-83f1b8ee7220
ba8f758f-810f-469e-a498-80c54b1efa88	8	52a8dfd5-0604-4b92-b6fc-d418f62d74d8
91bb17b7-b5dd-405a-a8e2-861710c241f8	1	807399bb-bb84-42c6-8598-9e306076e60b
91bb17b7-b5dd-405a-a8e2-861710c241f8	2	5f895c44-08f4-4f64-97b1-527315c95fe2
91bb17b7-b5dd-405a-a8e2-861710c241f8	3	4a7640f6-ae58-4759-8ed3-e86b5be0d792
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
9d886774-e02a-453e-8bd0-89bdf5197c04	store	2026-10-05 11:42:28.759724+00	2026-10-05 11:42:28.780355+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T12:42:28.780374+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
31aad81e-49c3-4015-abf9-c830395cdbae	deploy	2026-10-05 11:42:28.902593+00	2026-10-05 11:42:28.918688+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:28.917772+01:00\\"}"}	unavailable	\N	nochange	ba8f758f-810f-469e-a498-80c54b1efa88	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
8b03270d-ec11-4f2d-af31-e640dad2a81f	deploy	2026-10-05 11:42:28.933377+00	2026-10-05 11:42:28.942141+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:28.941291+01:00\\"}"}	unavailable	\N	nochange	ba8f758f-810f-469e-a498-80c54b1efa88	1	{"fs::File[localhost,path=/tmp/test],v=1"}
b2ebefc2-e061-44db-b774-b08fc6d67af7	store	2026-10-05 11:42:34.359053+00	2026-10-05 11:42:34.384678+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T12:42:34.384708+01:00\\"}"}	\N	\N	\N	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
480fe561-f677-4082-9571-82e0b896eb25	deploy	2026-10-05 11:42:34.56121+00	2026-10-05 11:42:34.574591+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:34.573893+01:00\\"}"}	unavailable	\N	nochange	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
8ff76920-40e8-4989-b052-77aa3dd9e07c	deploy	2026-10-05 11:42:34.595716+00	2026-10-05 11:42:34.609203+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:34.607510+01:00\\"}"}	unavailable	\N	nochange	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1	{"fs::File[localhost,path=/tmp/test],v=1"}
bedf1bd8-e220-4101-bf67-6da84e2cf11e	store	2026-10-05 11:42:35.829697+00	2026-10-05 11:42:35.834062+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-05T12:42:35.834082+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
26c60186-0be5-42a0-bd66-2c3e78deb174	store	2026-10-05 11:42:37.163902+00	2026-10-05 11:42:37.178934+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-05T12:42:37.178959+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	3	{"std::AgentConfig[internal,agentname=localhost],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
e9571715-9109-4df2-97cd-316cfbf16c41	deploy	2026-10-05 11:42:37.332567+00	2026-10-05 11:42:37.35417+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-05T12:42:37.353129+01:00\\"}"}	unavailable	\N	nochange	ba8f758f-810f-469e-a498-80c54b1efa88	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
68bba334-f1af-42b4-968d-359a7d49519d	store	2026-10-05 11:42:38.521683+00	2026-10-05 11:42:38.533834+00	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-05T12:42:38.533851+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	4	{"fs::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
80c18384-13a9-4e52-add9-330102bea9b8	store	2026-10-05 11:42:39.875737+00	2026-10-05 11:42:39.884137+00	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-05T12:42:39.884159+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	5	{"fs::File[localhost,path=/tmp/test],v=5","std::AgentConfig[internal,agentname=localhost],v=5"}
fd5c6b16-f35d-4d06-85a4-b6ff85147bbd	store	2026-10-05 11:42:44.334172+00	2026-10-05 11:42:44.343362+00	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-05T12:42:44.343384+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	6	{"std::AgentConfig[internal,agentname=localhost],v=6","fs::File[localhost,path=/tmp/test],v=6"}
86043db1-a0a0-4ee8-a50b-50d53b93d7ae	store	2026-10-05 11:42:44.542113+00	2026-10-05 11:42:44.547323+00	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-05T12:42:44.547332+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent3,key=key3],v=7","std::AgentConfig[internal,agentname=localhost],v=7","test::Resource[agent2,key=key2],v=7"}
3708c0a3-d0e2-4ce6-8c7c-5ce27968ca61	deploy	2026-10-05 11:42:44.595434+00	2026-10-05 11:42:44.608419+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-05T12:42:44.607247+01:00\\"}"}	unavailable	\N	nochange	ba8f758f-810f-469e-a498-80c54b1efa88	7	{"test::Resource[agent2,key=key2],v=7"}
ec602a44-63e2-4efc-88a9-046aae632344	deploy	2026-10-05 11:42:44.608552+00	2026-10-05 11:42:44.620329+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-05T12:42:44.618538+01:00\\"}"}	unavailable	\N	nochange	ba8f758f-810f-469e-a498-80c54b1efa88	7	{"test::Resource[agent3,key=key3],v=7"}
135b7fac-4781-47af-9e77-38f69c93f39c	store	2026-10-05 11:42:44.725965+00	2026-10-05 11:42:44.731778+00	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-05T12:42:44.731786+01:00\\"}"}	\N	\N	\N	ba8f758f-810f-469e-a498-80c54b1efa88	8	{"std::AgentConfig[internal,agentname=localhost],v=8","fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	store	2026-10-05 11:42:44.9825+00	2026-10-05 11:42:44.987985+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T12:42:44.988005+01:00\\"}"}	\N	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key4],v=1"}
c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	store	2026-10-05 11:42:45.302678+00	2026-10-05 11:42:45.307594+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-05T12:42:45.307603+01:00\\"}"}	\N	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	2	{"test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key10],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key5],v=2"}
e02cffe8-d779-49b0-b574-2188f2eafd05	deploy	2026-10-05 11:42:45.020173+00	2026-10-05 11:42:45.036297+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3c9e61f2-4fc8-49dc-8eda-bcce9b04365b).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"3c9e61f2-4fc8-49dc-8eda-bcce9b04365b\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.033523+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.034993+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 3c9e61f2-4fc8-49dc-8eda-bcce9b04365b) - duration: 0.0026 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.002562284469604492, \\"deploy_id\\": \\"3c9e61f2-4fc8-49dc-8eda-bcce9b04365b\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.036210+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Fail[agent1,key=key2],v=1"}
49ff1c64-c19f-4000-96fb-9ad77185fa90	deploy	2026-10-05 11:42:45.048884+00	2026-10-05 11:42:45.073053+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 530b3b47-d784-4afc-bb03-e75be3960236).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"530b3b47-d784-4afc-bb03-e75be3960236\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.061793+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 530b3b47-d784-4afc-bb03-e75be3960236) - duration: 0.0109 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.010926485061645508, \\"deploy_id\\": \\"530b3b47-d784-4afc-bb03-e75be3960236\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.072934+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key6],v=1"}
73f8e8ef-36c6-4bb3-b7b3-e35a7f1fd0d2	deploy	2026-10-05 11:42:45.083914+00	2026-10-05 11:42:45.095001+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2bfe90d1-d34b-470c-b81e-aba2a91b1522).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"2bfe90d1-d34b-470c-b81e-aba2a91b1522\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.094134+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.094485+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 2bfe90d1-d34b-470c-b81e-aba2a91b1522) - duration: 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0005922317504882812, \\"deploy_id\\": \\"2bfe90d1-d34b-470c-b81e-aba2a91b1522\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.094895+01:00\\"}"}	skipped	\N	nochange	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key3],v=1"}
78c20624-ce7b-4387-8663-4096de428557	deploy	2026-10-05 11:42:45.107316+00	2026-10-05 11:42:45.132981+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 43b4324d-9bca-4770-8194-56dadfc2898a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"43b4324d-9bca-4770-8194-56dadfc2898a\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.121566+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 43b4324d-9bca-4770-8194-56dadfc2898a) - duration: 0.0112 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.011150598526000977, \\"deploy_id\\": \\"43b4324d-9bca-4770-8194-56dadfc2898a\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.132880+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key1],v=1"}
00a12292-75c7-43e4-a037-d6cc0f6400c3	dryrun	2026-10-05 11:42:45.260838+00	2026-10-05 11:42:45.261559+00	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.260969+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.000461578369140625, \\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.261529+01:00\\"}"}	dry	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Fail[agent1,key=key2],v=1"}
39ba0437-3b5e-4a86-bd2a-398e2fa62417	dryrun	2026-10-05 11:42:45.304202+00	2026-10-05 11:42:45.304755+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.304296+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003409385681152344, \\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.304726+01:00\\"}"}	dry	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key1],v=1"}
bd58a64c-06e3-4ece-86c9-778ff677e816	dryrun	2026-10-05 11:42:45.327136+00	2026-10-05 11:42:45.327762+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.327241+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0004191398620605469, \\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.327739+01:00\\"}"}	dry	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key3],v=1"}
f81418d2-3839-44cc-9728-a194042781ec	deploy	2026-10-05 11:42:45.367617+00	2026-10-05 11:42:45.395797+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 8a070989-c4e0-4dcc-a6c1-0dda70f53d04).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"8a070989-c4e0-4dcc-a6c1-0dda70f53d04\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.377067+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 8a070989-c4e0-4dcc-a6c1-0dda70f53d04) - duration: 0.0185 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.01851058006286621, \\"deploy_id\\": \\"8a070989-c4e0-4dcc-a6c1-0dda70f53d04\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.395722+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	91bb17b7-b5dd-405a-a8e2-861710c241f8	2	{"test::Resource[agent1,key=key7],v=2"}
ebb9027e-bd5b-4b0b-91ec-c5a0dc896a65	deploy	2026-10-05 11:42:45.408688+00	2026-10-05 11:42:45.437226+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: dbf1a766-7451-408f-9eb2-9b5a0ecd7c7d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"dbf1a766-7451-408f-9eb2-9b5a0ecd7c7d\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.421916+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.422310+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: dbf1a766-7451-408f-9eb2-9b5a0ecd7c7d) - duration: 0.0150 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.014963388442993164, \\"deploy_id\\": \\"dbf1a766-7451-408f-9eb2-9b5a0ecd7c7d\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.437086+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	91bb17b7-b5dd-405a-a8e2-861710c241f8	2	{"test::Resource[agent1,key=key11],v=2"}
05daffd3-1db3-4048-9508-01ac10433046	deploy	2026-10-05 11:42:45.453021+00	2026-10-05 11:42:45.473715+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 65117d85-56c1-4232-8ca7-5f5b862a381a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"65117d85-56c1-4232-8ca7-5f5b862a381a\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.464401+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.464881+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 65117d85-56c1-4232-8ca7-5f5b862a381a) - duration: 0.0090 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.009019613265991211, \\"deploy_id\\": \\"65117d85-56c1-4232-8ca7-5f5b862a381a\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.473589+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	91bb17b7-b5dd-405a-a8e2-861710c241f8	2	{"test::Resource[agent1,key=key10],v=2"}
849b876a-42ca-4fad-83bf-8406d8ab1340	deploy	2026-10-05 11:42:45.484907+00	2026-10-05 11:42:45.502464+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 794f0ae8-db85-494c-9b9e-7b55ad2ac640).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"794f0ae8-db85-494c-9b9e-7b55ad2ac640\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.494906+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 794f0ae8-db85-494c-9b9e-7b55ad2ac640) - duration: 0.0073 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.00734257698059082, \\"deploy_id\\": \\"794f0ae8-db85-494c-9b9e-7b55ad2ac640\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.502384+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	91bb17b7-b5dd-405a-a8e2-861710c241f8	2	{"test::Resource[agent1,key=key9],v=2"}
a39fd61d-d7e9-42a5-bdc3-ffa155098b4a	dryrun	2026-10-05 11:42:45.51236+00	2026-10-05 11:42:45.513119+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.512535+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00039315223693847656, \\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.513069+01:00\\"}"}	dry	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key5],v=1"}
6c21bb16-d953-41b8-a30d-a3521d58fa87	dryrun	2026-10-05 11:42:45.52811+00	2026-10-05 11:42:45.529157+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.528317+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: edfd45cd-b3dd-471d-a7d9-7c9ef876f311 - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005559921264648438, \\"dry_run_id\\": \\"edfd45cd-b3dd-471d-a7d9-7c9ef876f311\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-05T12:42:45.529081+01:00\\"}"}	dry	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	1	{"test::Resource[agent1,key=key6],v=1"}
4abf908e-2fdf-4f74-8810-ba6f0c84f981	store	2026-10-05 11:42:45.61832+00	2026-10-05 11:42:45.626489+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-05T12:42:45.626506+01:00\\"}"}	\N	\N	\N	91bb17b7-b5dd-405a-a8e2-861710c241f8	3	{"test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key4],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
ba8f758f-810f-469e-a498-80c54b1efa88	9d886774-e02a-453e-8bd0-89bdf5197c04	fs::File[localhost,path=/tmp/test]	1
ba8f758f-810f-469e-a498-80c54b1efa88	9d886774-e02a-453e-8bd0-89bdf5197c04	std::AgentConfig[internal,agentname=localhost]	1
ba8f758f-810f-469e-a498-80c54b1efa88	31aad81e-49c3-4015-abf9-c830395cdbae	std::AgentConfig[internal,agentname=localhost]	1
ba8f758f-810f-469e-a498-80c54b1efa88	8b03270d-ec11-4f2d-af31-e640dad2a81f	fs::File[localhost,path=/tmp/test]	1
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	b2ebefc2-e061-44db-b774-b08fc6d67af7	fs::File[localhost,path=/tmp/test]	1
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	b2ebefc2-e061-44db-b774-b08fc6d67af7	std::AgentConfig[internal,agentname=localhost]	1
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	480fe561-f677-4082-9571-82e0b896eb25	std::AgentConfig[internal,agentname=localhost]	1
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	8ff76920-40e8-4989-b052-77aa3dd9e07c	fs::File[localhost,path=/tmp/test]	1
ba8f758f-810f-469e-a498-80c54b1efa88	bedf1bd8-e220-4101-bf67-6da84e2cf11e	std::AgentConfig[internal,agentname=localhost]	2
ba8f758f-810f-469e-a498-80c54b1efa88	bedf1bd8-e220-4101-bf67-6da84e2cf11e	fs::File[localhost,path=/tmp/test]	2
ba8f758f-810f-469e-a498-80c54b1efa88	26c60186-0be5-42a0-bd66-2c3e78deb174	std::AgentConfig[internal,agentname=localhost]	3
ba8f758f-810f-469e-a498-80c54b1efa88	26c60186-0be5-42a0-bd66-2c3e78deb174	fs::File[localhost,path=/tmp/test_orphan]	3
ba8f758f-810f-469e-a498-80c54b1efa88	26c60186-0be5-42a0-bd66-2c3e78deb174	fs::File[localhost,path=/tmp/test]	3
ba8f758f-810f-469e-a498-80c54b1efa88	e9571715-9109-4df2-97cd-316cfbf16c41	fs::File[localhost,path=/tmp/test_orphan]	3
ba8f758f-810f-469e-a498-80c54b1efa88	68bba334-f1af-42b4-968d-359a7d49519d	fs::File[localhost,path=/tmp/test]	4
ba8f758f-810f-469e-a498-80c54b1efa88	68bba334-f1af-42b4-968d-359a7d49519d	std::AgentConfig[internal,agentname=localhost]	4
ba8f758f-810f-469e-a498-80c54b1efa88	80c18384-13a9-4e52-add9-330102bea9b8	fs::File[localhost,path=/tmp/test]	5
ba8f758f-810f-469e-a498-80c54b1efa88	80c18384-13a9-4e52-add9-330102bea9b8	std::AgentConfig[internal,agentname=localhost]	5
ba8f758f-810f-469e-a498-80c54b1efa88	fd5c6b16-f35d-4d06-85a4-b6ff85147bbd	std::AgentConfig[internal,agentname=localhost]	6
ba8f758f-810f-469e-a498-80c54b1efa88	fd5c6b16-f35d-4d06-85a4-b6ff85147bbd	fs::File[localhost,path=/tmp/test]	6
ba8f758f-810f-469e-a498-80c54b1efa88	86043db1-a0a0-4ee8-a50b-50d53b93d7ae	fs::File[localhost,path=/tmp/test]	7
ba8f758f-810f-469e-a498-80c54b1efa88	86043db1-a0a0-4ee8-a50b-50d53b93d7ae	test::Resource[agent3,key=key3]	7
ba8f758f-810f-469e-a498-80c54b1efa88	86043db1-a0a0-4ee8-a50b-50d53b93d7ae	std::AgentConfig[internal,agentname=localhost]	7
ba8f758f-810f-469e-a498-80c54b1efa88	86043db1-a0a0-4ee8-a50b-50d53b93d7ae	test::Resource[agent2,key=key2]	7
ba8f758f-810f-469e-a498-80c54b1efa88	3708c0a3-d0e2-4ce6-8c7c-5ce27968ca61	test::Resource[agent2,key=key2]	7
ba8f758f-810f-469e-a498-80c54b1efa88	ec602a44-63e2-4efc-88a9-046aae632344	test::Resource[agent3,key=key3]	7
ba8f758f-810f-469e-a498-80c54b1efa88	135b7fac-4781-47af-9e77-38f69c93f39c	std::AgentConfig[internal,agentname=localhost]	8
ba8f758f-810f-469e-a498-80c54b1efa88	135b7fac-4781-47af-9e77-38f69c93f39c	fs::File[localhost,path=/tmp/test]	8
ba8f758f-810f-469e-a498-80c54b1efa88	135b7fac-4781-47af-9e77-38f69c93f39c	test::Resource[agent2,key=key2]	8
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Resource[agent1,key=key3]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Resource[agent1,key=key1]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Resource[agent1,key=key6]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Resource[agent1,key=key5]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Fail[agent1,key=key2]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	3c5d99f0-ac62-4f1b-8aaa-b5eb1609d34e	test::Resource[agent1,key=key4]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	e02cffe8-d779-49b0-b574-2188f2eafd05	test::Fail[agent1,key=key2]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	49ff1c64-c19f-4000-96fb-9ad77185fa90	test::Resource[agent1,key=key6]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	73f8e8ef-36c6-4bb3-b7b3-e35a7f1fd0d2	test::Resource[agent1,key=key3]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	78c20624-ce7b-4387-8663-4096de428557	test::Resource[agent1,key=key1]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	00a12292-75c7-43e4-a037-d6cc0f6400c3	test::Fail[agent1,key=key2]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key7]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key4]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key10]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Fail[agent1,key=key2]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key11]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key3]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key1]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key9]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	c76790c7-0fdf-4dbc-9cf9-5b34edb72bca	test::Resource[agent1,key=key5]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	39ba0437-3b5e-4a86-bd2a-398e2fa62417	test::Resource[agent1,key=key1]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	bd58a64c-06e3-4ece-86c9-778ff677e816	test::Resource[agent1,key=key3]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	f81418d2-3839-44cc-9728-a194042781ec	test::Resource[agent1,key=key7]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	ebb9027e-bd5b-4b0b-91ec-c5a0dc896a65	test::Resource[agent1,key=key11]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	05daffd3-1db3-4048-9508-01ac10433046	test::Resource[agent1,key=key10]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	849b876a-42ca-4fad-83bf-8406d8ab1340	test::Resource[agent1,key=key9]	2
91bb17b7-b5dd-405a-a8e2-861710c241f8	a39fd61d-d7e9-42a5-bdc3-ffa155098b4a	test::Resource[agent1,key=key5]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	6c21bb16-d953-41b8-a30d-a3521d58fa87	test::Resource[agent1,key=key6]	1
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key5]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Fail[agent1,key=key2]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key3]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key1]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key7]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key8]	3
91bb17b7-b5dd-405a-a8e2-861710c241f8	4abf908e-2fdf-4f74-8810-ba6f0c84f981	test::Resource[agent1,key=key4]	3
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
5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	1
ba8f758f-810f-469e-a498-80c54b1efa88	8
91bb17b7-b5dd-405a-a8e2-861710c241f8	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
NOSdrive	ba8f758f-810f-469e-a498-80c54b1efa88	2026-10-05 11:42:21.636715+00	\N	90f6f2f8-e83d-42bd-810d-c2591bae58c4
NOSdrive	5e5a1fd5-ecae-46fa-bd91-ff7be937e7e5	2026-10-05 11:42:21.76938+00	\N	68733ab0-2aeb-4765-b92b-8ef0b7291ca1
NOSdrive	91bb17b7-b5dd-405a-a8e2-861710c241f8	2026-10-05 11:42:44.813245+00	2026-10-05 11:42:45.60424+00	c937bbb4-0b31-4e51-9bb7-b2864c0d40e8
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050}
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

--\unrestrict SnUAYhTznxDEiGTdqmukMCexBbUo6feDAiigIL3wEdVDBMq3bXJRjUsbn0bhiWD

