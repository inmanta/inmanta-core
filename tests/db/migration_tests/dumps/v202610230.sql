--
-- PostgreSQL database dump
--

--\restrict 0PzVM3p5UDIUpnHW8pWO9Za1DNY1ccIuAane8WaUv0phJY6H2cOJL0t91p28MxD

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
    resource_filter jsonb,
    context jsonb,
    status character varying DEFAULT 'started'::character varying NOT NULL,
    error character varying
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
    requirements character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL,
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
af3a3d3d-b09a-4aec-a667-e0cf08639caa	$__scheduler	f	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	$__scheduler	f	\N
f5e99317-ff7d-449f-b10f-451c2cf4d394	$__scheduler	f	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	localhost	f	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	localhost	f	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	internal	f	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	agent2	f	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	agent3	f	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	agent1	t	t
a4cd0d2c-623c-4219-99c1-d21764b8c9af	$__scheduler	t	t
85a702eb-578e-47fc-8c64-eb1fa372059b	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
1	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
1	internal	std	62a46f65-f2a1-45ba-b22b-e0faf8479463
1	localhost	fs	62a46f65-f2a1-45ba-b22b-e0faf8479463
2	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
2	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
3	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
3	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
4	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
4	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
5	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
5	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
6	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
6	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
7	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
7	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
8	localhost	fs	af3a3d3d-b09a-4aec-a667-e0cf08639caa
8	localhost	std	af3a3d3d-b09a-4aec-a667-e0cf08639caa
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
d3265544-02ba-4f3b-a281-e78607b0f293	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:17.828371+00	2026-10-23 14:53:24.798151+00	2026-10-23 14:53:17.809694+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	e2e172a3-7f2d-4b5c-b441-0fd6bfa9cc1d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
8323a41c-42f7-48f7-93fc-f545e77e6a14	62a46f65-f2a1-45ba-b22b-e0faf8479463	2026-10-23 14:53:25.074697+00	2026-10-23 14:53:29.996886+00	2026-10-23 14:53:25.059111+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	9a18893e-553c-445f-8464-98f8695c05a3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
8b945857-7402-4258-ab5a-19d45c933de8	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:30.198867+00	2026-10-23 14:53:31.318279+00	2026-10-23 14:53:30.184916+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	9bfe16cc-b2ed-44d6-a0ff-439d779ab620	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
64e1f512-daf6-4289-adc9-4495ccc5a7c5	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:31.422439+00	2026-10-23 14:53:32.58358+00	2026-10-23 14:53:31.401912+00	{}	{"add_one_resource": "true"}	t	f	t	3	b8d21df8-a5ed-40c3-a9aa-09b270da91cc	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
d328141a-859d-49fe-b25e-a2ff66395bf6	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:32.802165+00	2026-10-23 14:53:33.942799+00	2026-10-23 14:53:32.788449+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	06caca0a-e9ce-4129-9270-c61efad5de19	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
e6dbcf13-0ca6-4efc-9b51-7d1e8e41b155	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:34.120904+00	2026-10-23 14:53:35.245645+00	2026-10-23 14:53:34.109133+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	fb21dac7-ed87-4cbf-ac53-6b46b1b5ace6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
cc7c71f4-e53a-4556-9549-e6dff2182f9c	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:35.362563+00	2026-10-23 14:53:39.74515+00	2026-10-23 14:53:35.34767+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	5a9ea631-aed4-45e0-b3c9-ac6eae336754	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
7b457251-12a9-4028-a71e-0b3dc1de0cfc	85a702eb-578e-47fc-8c64-eb1fa372059b	2026-10-23 14:53:41.255462+00	2026-10-23 14:53:41.299893+00	2026-10-23 14:53:41.202714+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	91b6d61f-36e6-4280-86ad-e9ca3d360dda	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:24.734292+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2026-10-23 14:53:40.285482+00	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
1	62a46f65-f2a1-45ba-b22b-e0faf8479463	2026-10-23 14:53:29.937312+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:31.256922+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:32.521522+00	t	{"export_metadata": {"type": "manual", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:33.872894+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:35.188699+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:39.688257+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
2	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2026-10-23 14:53:40.650603+00	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:39.865241+00	t	\N	3	{}	{}	6	t	\N	\N
8	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:40.045833+00	t	\N	2	{}	{}	7	t	\N	\N
3	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2026-10-23 14:53:40.980896+00	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	1	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	1	fs	1.2.0
62a46f65-f2a1-45ba-b22b-e0faf8479463	1	std	7.0.0
62a46f65-f2a1-45ba-b22b-e0faf8479463	1	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	2	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	2	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	3	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	3	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	4	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	4	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	5	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	5	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	6	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	6	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	std	8.7.5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8	fs	1.2.0
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	discovery::Discovered[myagent,name=discovered]	{}	2026-10-23 14:53:41.019366+00	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
af3a3d3d-b09a-4aec-a667-e0cf08639caa	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-23 14:53:41.019447+00	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context, status, error) FROM stdin;
4cbededf-73e6-49ca-a9ce-3c4c25267061	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	2026-10-23 14:53:40.573964+00	6	0	{"03090acc-3dc1-520b-9c47-4a19ad5d0af0": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "13942934-d474-5af1-9dca-91c816912f80": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "3b8a1315-ff18-5c9f-a9c2-7c5f7516acde": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "538bc3cd-da0e-5094-8eaf-d9b765f1a426": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "7bec37f2-cf20-5ad2-83c8-8d91f1462929": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "cab28611-8880-58b7-b9f3-6f74941b25b5": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}}	\N	\N	started	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
f5e99317-ff7d-449f-b10f-451c2cf4d394	dev-2	9eaa0c82-1fca-4d73-a41a-159af504203e			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
85a702eb-578e-47fc-8c64-eb1fa372059b	dev-4	9eaa0c82-1fca-4d73-a41a-159af504203e			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
af3a3d3d-b09a-4aec-a667-e0cf08639caa	dev-1	9eaa0c82-1fca-4d73-a41a-159af504203e			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
62a46f65-f2a1-45ba-b22b-e0faf8479463	dev-1-twin	9eaa0c82-1fca-4d73-a41a-159af504203e			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
a4cd0d2c-623c-4219-99c1-d21764b8c9af	dev-3	9eaa0c82-1fca-4d73-a41a-159af504203e			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	af3a3d3d-b09a-4aec-a667-e0cf08639caa	{}	f
fs	1.2.0	af3a3d3d-b09a-4aec-a667-e0cf08639caa	{}	f
std	7.0.0	62a46f65-f2a1-45ba-b22b-e0faf8479463	{}	f
fs	1.2.0	62a46f65-f2a1-45ba-b22b-e0faf8479463	{}	f
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
9aa74ebf-f0c6-40b9-a446-c6d5073227c3	85a702eb-578e-47fc-8c64-eb1fa372059b	2026-10-23 14:53:41.314034+00	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/7b457251-12a9-4028-a71e-0b3dc1de0cfc	f	f	7b457251-12a9-4028-a71e-0b3dc1de0cfc
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
0c653964-38de-4bec-9d40-479b04460cb6	fact1	value1	af3a3d3d-b09a-4aec-a667-e0cf08639caa	std::testing::NullResource[localhost,name=test1]	fact	2026-10-23 14:53:34.032907+00	{}	f
3da2a9c7-b358-47b6-966d-8fb96dac9015	fact2	value2	af3a3d3d-b09a-4aec-a667-e0cf08639caa	std::testing::NullResource[localhost,name=test2]	fact	2026-10-23 14:53:34.052326+00	{}	t
47fe5969-1e65-4f32-8445-8e28c55227a2	fact3	value3	af3a3d3d-b09a-4aec-a667-e0cf08639caa	std::testing::NullResource[localhost,name=test3]	fact	2026-10-23 14:53:34.065016+00	{}	t
c5301cd3-4fd1-4f08-b895-7b0c36cb2634	parameter1	value1	af3a3d3d-b09a-4aec-a667-e0cf08639caa		fact	2026-10-23 14:53:34.075787+00	{}	f
25d59a2e-d289-45d1-867e-0d6490f0f190	parameter2	value2	af3a3d3d-b09a-4aec-a667-e0cf08639caa		fact	2026-10-23 14:53:34.086426+00	{}	f
8391634d-a935-41f0-adeb-92a7f378bd54	parameter3	value3	af3a3d3d-b09a-4aec-a667-e0cf08639caa		fact	2026-10-23 14:53:34.097271+00	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
9eaa0c82-1fca-4d73-a41a-159af504203e	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
a98f586f-127e-4cdf-8574-cd1b58126716	2026-10-23 14:53:17.83543+00	2026-10-23 14:53:17.854912+00		Init		Using extra environment variables during compile \n	0	d3265544-02ba-4f3b-a281-e78607b0f293
95b36c5e-cf7d-4d02-96d8-99a4d30e0182	2026-10-23 14:53:17.863062+00	2026-10-23 14:53:17.88329+00		Venv check		Creating new venv at /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env-py3.14\n	0	d3265544-02ba-4f3b-a281-e78607b0f293
50291476-f8fa-4058-bbdb-649fc67bf6b1	2026-10-23 14:53:17.895602+00	2026-10-23 14:53:18.259551+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	d3265544-02ba-4f3b-a281-e78607b0f293
f6870067-1756-4a66-aeab-006189bb29f8	2026-10-23 14:53:32.866233+00	2026-10-23 14:53:33.933713+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpiwfr_ni7 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.056 seconds\ncompiler       DEBUG   The entire export command took 0.124 seconds\n	0	d328141a-859d-49fe-b25e-a2ff66395bf6
372f8d1e-fcd7-4605-a262-5edf4a107ccb	2026-10-23 14:53:28.941387+00	2026-10-23 14:53:29.987346+00	/tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 62a46f65-f2a1-45ba-b22b-e0faf8479463 --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp6qducmxq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.057 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.061 seconds\ncompiler       DEBUG   The entire export command took 0.152 seconds\n	0	8323a41c-42f7-48f7-93fc-f545e77e6a14
271036fc-b360-4058-bfca-0b5123447b7f	2026-10-23 14:53:32.809651+00	2026-10-23 14:53:32.831368+00		Init		Using extra environment variables during compile \n	0	d328141a-859d-49fe-b25e-a2ff66395bf6
b0e9cb5e-c40e-4471-ae10-16d4750d3f84	2026-10-23 14:53:32.841045+00	2026-10-23 14:53:32.858397+00		Venv check		Found existing venv\n	0	d328141a-859d-49fe-b25e-a2ff66395bf6
d14e7f2f-df4f-4310-af45-b40ee7c4dc6a	2026-10-23 14:53:25.082883+00	2026-10-23 14:53:25.102968+00		Init		Using extra environment variables during compile \n	0	8323a41c-42f7-48f7-93fc-f545e77e6a14
6b9f5563-51c0-492f-80a1-173d7d2bfa63	2026-10-23 14:53:25.111434+00	2026-10-23 14:53:25.128004+00		Venv check		Creating new venv at /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env-py3.14\n	0	8323a41c-42f7-48f7-93fc-f545e77e6a14
c59d5543-9faa-469b-b8c4-cb6c2ff67a35	2026-10-23 14:53:25.137614+00	2026-10-23 14:53:25.384058+00	/tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	8323a41c-42f7-48f7-93fc-f545e77e6a14
67fd2d70-7ffd-40c8-b507-5bf64ca5244e	2026-10-23 14:53:23.724059+00	2026-10-23 14:53:24.789952+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpfp2lk97a --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.023 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.035 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.064 seconds\ncompiler       DEBUG   The entire export command took 0.147 seconds\n	0	d3265544-02ba-4f3b-a281-e78607b0f293
e4a3647c-b3cf-420f-8ce8-24fefb3fc58f	2026-10-23 14:53:30.206849+00	2026-10-23 14:53:30.233077+00		Init		Using extra environment variables during compile \n	0	8b945857-7402-4258-ab5a-19d45c933de8
6b3b14a5-f5b3-480d-94e2-726df49554d2	2026-10-23 14:53:30.243057+00	2026-10-23 14:53:30.262029+00		Venv check		Found existing venv\n	0	8b945857-7402-4258-ab5a-19d45c933de8
80c141c0-2c0c-4cd6-a25f-fa7300289e51	2026-10-23 14:53:41.265463+00	2026-10-23 14:53:41.291889+00		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpktgxj4ws/server/85a702eb-578e-47fc-8c64-eb1fa372059b/compiler and no repository set.\n	1	7b457251-12a9-4028-a71e-0b3dc1de0cfc
9093a0b4-90c1-434c-9acf-25bfc4846f98	2026-10-23 14:53:31.494067+00	2026-10-23 14:53:32.573437+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpyijwn_u0 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.035 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.060 seconds\ncompiler       DEBUG   The entire export command took 0.129 seconds\n	0	64e1f512-daf6-4289-adc9-4495ccc5a7c5
b2ceed70-921c-40cc-b78a-4824a64ddad7	2026-10-23 14:53:30.270675+00	2026-10-23 14:53:31.309766+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmptelj6caj --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.043 seconds\ncompiler       DEBUG   The entire export command took 0.112 seconds\n	0	8b945857-7402-4258-ab5a-19d45c933de8
ad64b123-3f58-482a-905e-a68d51c381fd	2026-10-23 14:53:31.431274+00	2026-10-23 14:53:31.456461+00		Init		Using extra environment variables during compile add_one_resource='true'\n	0	64e1f512-daf6-4289-adc9-4495ccc5a7c5
cba13dac-bf67-43da-be69-dd44b87c6040	2026-10-23 14:53:18.267181+00	2026-10-23 14:53:23.716234+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp2btlphjo:\n                                 Pip command: /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp2btlphjo inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.12.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Downloading jsonpath_ng-1.13.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Downloading jsonpath_ng-1.13.0-py3-none-any.whl (83 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (529 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: tornado, mitogen, jsonpath-ng, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.12.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.13.0 mitogen-0.3.54 tornado-6.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	d3265544-02ba-4f3b-a281-e78607b0f293
749a7f68-958b-4e1d-bcf8-3234b4c3c21f	2026-10-23 14:53:31.465199+00	2026-10-23 14:53:31.484668+00		Venv check		Found existing venv\n	0	64e1f512-daf6-4289-adc9-4495ccc5a7c5
910b81a1-ddc4-42a4-ac1a-249259993064	2026-10-23 14:53:34.187069+00	2026-10-23 14:53:35.236844+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1ssqx8f0 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.026 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.043 seconds\ncompiler       DEBUG   The entire export command took 0.105 seconds\n	0	e6dbcf13-0ca6-4efc-9b51-7d1e8e41b155
fb6f6d6f-ff8f-4e06-99df-5ef7cee9036f	2026-10-23 14:53:35.370656+00	2026-10-23 14:53:35.396942+00		Init		Using extra environment variables during compile \n	0	cc7c71f4-e53a-4556-9549-e6dff2182f9c
d6668d97-6a47-4fce-93de-ea7500c91d3d	2026-10-23 14:53:35.4059+00	2026-10-23 14:53:35.424773+00		Venv check		Found existing venv\n	0	cc7c71f4-e53a-4556-9549-e6dff2182f9c
2de12e20-ed41-43b5-ac0d-92f465154e56	2026-10-23 14:53:35.436621+00	2026-10-23 14:53:35.661594+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	cc7c71f4-e53a-4556-9549-e6dff2182f9c
fc1b083a-1d15-45d8-81ff-aab34676401b	2026-10-23 14:53:25.391619+00	2026-10-23 14:53:28.93333+00	/tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpiyb7igea:\n                                 Pip command: /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpiyb7igea inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.12.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.13.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.13.0-py3-none-any.whl (83 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (529 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: tornado, mitogen, jsonpath-ng, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.12.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpktgxj4ws/server/62a46f65-f2a1-45ba-b22b-e0faf8479463/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.13.0 mitogen-0.3.54 tornado-6.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	8323a41c-42f7-48f7-93fc-f545e77e6a14
6217191c-b70f-40a7-961f-8106ff2a0522	2026-10-23 14:53:34.128294+00	2026-10-23 14:53:34.150145+00		Init		Using extra environment variables during compile \n	0	e6dbcf13-0ca6-4efc-9b51-7d1e8e41b155
d9b3f573-d679-4bc1-9d1c-6262a4232f73	2026-10-23 14:53:34.159095+00	2026-10-23 14:53:34.177613+00		Venv check		Found existing venv\n	0	e6dbcf13-0ca6-4efc-9b51-7d1e8e41b155
6d6a7c9c-342a-4d58-a0e0-bb064a236bc2	2026-10-23 14:53:35.66913+00	2026-10-23 14:53:38.668379+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp9ri0t3uv:\n                                 Pip command: /tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp9ri0t3uv inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/a60872a1-8b10-4cec-9110-89565e5f6d47/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	cc7c71f4-e53a-4556-9549-e6dff2182f9c
110234bb-2e67-4c09-a9cc-982a965e88d6	2026-10-23 14:53:38.685702+00	2026-10-23 14:53:39.735612+00	/tmp/tmpktgxj4ws/server/af3a3d3d-b09a-4aec-a667-e0cf08639caa/compiler/.env/bin/python -m inmanta.app -vvv export -X -e af3a3d3d-b09a-4aec-a667-e0cf08639caa --server_address localhost --server_port 36983 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpn1fc29_y --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.033 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36983/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36983/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.043 seconds\ncompiler       DEBUG   The entire export command took 0.111 seconds\n	0	cc7c71f4-e53a-4556-9549-e6dff2182f9c
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	f11e928c-0d9d-4ccf-bb04-e5a411749727
62a46f65-f2a1-45ba-b22b-e0faf8479463	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	06444793-03c8-44a5-8c37-16aa96182b76
62a46f65-f2a1-45ba-b22b-e0faf8479463	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	06444793-03c8-44a5-8c37-16aa96182b76
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	aaa6f1ea-1006-4441-b61d-f0044907211f
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	42f407a3-0267-40cc-bd60-03ee9b0d304d
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	42f407a3-0267-40cc-bd60-03ee9b0d304d
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b6d1e9e9-dfd2-43f3-a325-3c72b7cf052f
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	65a4e0b1-ce34-4f89-abeb-4dc730e76f28
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a9d250e6-ef3b-444c-bfbe-af3e1b6fe940
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3ae6c01b-53ab-4f59-8904-493829df931d
af3a3d3d-b09a-4aec-a667-e0cf08639caa	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	f3954ea9-6cb5-4410-89cf-2fea3fb37c16
af3a3d3d-b09a-4aec-a667-e0cf08639caa	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	143f94d2-4e6a-41b9-b06e-f75138918adc
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	994f50ad-e0f5-4b8f-9a73-7f058268bfdc
af3a3d3d-b09a-4aec-a667-e0cf08639caa	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	731529c0-30a8-4188-8a23-fdc7704e984e
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	eaa67e4b-0878-47c5-93e3-0551ae079457
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	eaa67e4b-0878-47c5-93e3-0551ae079457
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
3c660858-2e43-4e94-b130-5c3f4fa308e6	a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-23 14:53:40.78482+00
89b5d88d-826c-410f-b216-3833c6deae23	a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-23 14:53:40.82364+00
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-23 14:53:40.311362+00	\N	\N	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test]	2026-10-23 14:53:24.963718+00	\N	2026-10-23 14:53:24.963718+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:24.906439+00	f	\N	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Fail[agent1,key=key2]	2026-10-23 14:53:40.345054+00	\N	2026-10-23 14:53:40.345054+00	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:40.311362+00	f	\N	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key7]	2026-10-23 14:53:40.756301+00	2026-10-23 14:53:40.734002+00	2026-10-23 14:53:40.756301+00	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.676153+00	t	\N	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key1]	2026-10-23 14:53:40.388034+00	2026-10-23 14:53:40.359433+00	2026-10-23 14:53:40.388034+00	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.311362+00	t	\N	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	std::AgentConfig[internal,agentname=localhost]	2026-10-23 14:53:30.087624+00	\N	2026-10-23 14:53:30.087624+00	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:30.045647+00	f	\N	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	fs::File[localhost,path=/tmp/test]	2026-10-23 14:53:30.108568+00	\N	2026-10-23 14:53:30.108568+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:30.045647+00	f	\N	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key10]	2026-10-23 14:53:40.78482+00	\N	2026-10-23 14:53:40.78482+00	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.676153+00	f	3c660858-2e43-4e94-b130-5c3f4fa308e6	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key3]	2026-10-23 14:53:40.449411+00	\N	2026-10-23 14:53:40.449411+00	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-23 14:53:40.311362+00	f	\N	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	fs::File[localhost,path=/tmp/test_orphan]	2026-10-23 14:53:32.680098+00	\N	2026-10-23 14:53:32.680098+00	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:32.649545+00	f	\N	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key11]	2026-10-23 14:53:40.82364+00	\N	2026-10-23 14:53:40.82364+00	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.676153+00	f	89b5d88d-826c-410f-b216-3833c6deae23	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	test::Resource[agent2,key=key2]	2026-10-23 14:53:39.940677+00	\N	2026-10-23 14:53:39.940677+00	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:39.905073+00	f	\N	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	test::Resource[agent3,key=key3]	2026-10-23 14:53:39.954535+00	\N	2026-10-23 14:53:39.954535+00	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-23 14:53:39.905073+00	f	\N	7
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-23 14:53:40.311362+00	\N	\N	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key6]	2026-10-23 14:53:40.425085+00	2026-10-23 14:53:40.397824+00	2026-10-23 14:53:40.425085+00	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.311362+00	t	\N	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	test::Resource[agent1,key=key9]	2026-10-23 14:53:40.72447+00	2026-10-23 14:53:40.709094+00	2026-10-23 14:53:40.72447+00	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-23 14:53:40.676153+00	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	f11e928c-0d9d-4ccf-bb04-e5a411749727	\N
62a46f65-f2a1-45ba-b22b-e0faf8479463	06444793-03c8-44a5-8c37-16aa96182b76	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	aaa6f1ea-1006-4441-b61d-f0044907211f	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	42f407a3-0267-40cc-bd60-03ee9b0d304d	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	b6d1e9e9-dfd2-43f3-a325-3c72b7cf052f	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	65a4e0b1-ce34-4f89-abeb-4dc730e76f28	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	a9d250e6-ef3b-444c-bfbe-af3e1b6fe940	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	3ae6c01b-53ab-4f59-8904-493829df931d	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	f3954ea9-6cb5-4410-89cf-2fea3fb37c16	set-a
af3a3d3d-b09a-4aec-a667-e0cf08639caa	143f94d2-4e6a-41b9-b06e-f75138918adc	set-b
af3a3d3d-b09a-4aec-a667-e0cf08639caa	994f50ad-e0f5-4b8f-9a73-7f058268bfdc	\N
af3a3d3d-b09a-4aec-a667-e0cf08639caa	731529c0-30a8-4188-8a23-fdc7704e984e	set-a
a4cd0d2c-623c-4219-99c1-d21764b8c9af	8b42bd9c-a709-4d35-8c7b-55b111a3702c	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	43b7be37-4445-47ab-9c34-590538ac6708	\N
a4cd0d2c-623c-4219-99c1-d21764b8c9af	eaa67e4b-0878-47c5-93e3-0551ae079457	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	1	f11e928c-0d9d-4ccf-bb04-e5a411749727
62a46f65-f2a1-45ba-b22b-e0faf8479463	1	06444793-03c8-44a5-8c37-16aa96182b76
af3a3d3d-b09a-4aec-a667-e0cf08639caa	2	aaa6f1ea-1006-4441-b61d-f0044907211f
af3a3d3d-b09a-4aec-a667-e0cf08639caa	3	42f407a3-0267-40cc-bd60-03ee9b0d304d
af3a3d3d-b09a-4aec-a667-e0cf08639caa	4	b6d1e9e9-dfd2-43f3-a325-3c72b7cf052f
af3a3d3d-b09a-4aec-a667-e0cf08639caa	5	65a4e0b1-ce34-4f89-abeb-4dc730e76f28
af3a3d3d-b09a-4aec-a667-e0cf08639caa	6	a9d250e6-ef3b-444c-bfbe-af3e1b6fe940
af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	3ae6c01b-53ab-4f59-8904-493829df931d
af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	f3954ea9-6cb5-4410-89cf-2fea3fb37c16
af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	143f94d2-4e6a-41b9-b06e-f75138918adc
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8	994f50ad-e0f5-4b8f-9a73-7f058268bfdc
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8	731529c0-30a8-4188-8a23-fdc7704e984e
a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	8b42bd9c-a709-4d35-8c7b-55b111a3702c
a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	43b7be37-4445-47ab-9c34-590538ac6708
a4cd0d2c-623c-4219-99c1-d21764b8c9af	3	eaa67e4b-0878-47c5-93e3-0551ae079457
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a42c9fc5-ba3c-41b8-bb2b-004e9982e8ea	store	2026-10-23 14:53:24.734162+00	2026-10-23 14:53:24.747286+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-23T15:53:24.747298+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	1	{"fs::File[localhost,path=/tmp/test],v=1"}
23c51aed-b2e1-4c72-9129-d49718208e01	deploy	2026-10-23 14:53:24.936993+00	2026-10-23 14:53:24.963718+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:24.962442+01:00\\"}"}	unavailable	\N	nochange	af3a3d3d-b09a-4aec-a667-e0cf08639caa	1	{"fs::File[localhost,path=/tmp/test],v=1"}
2485dfe6-2b27-4216-83ac-1bf11c2f361d	store	2026-10-23 14:53:29.936922+00	2026-10-23 14:53:29.952231+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-23T15:53:29.952274+01:00\\"}"}	\N	\N	\N	62a46f65-f2a1-45ba-b22b-e0faf8479463	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
62788570-f54e-4fdc-a420-681f4799c990	deploy	2026-10-23 14:53:30.062947+00	2026-10-23 14:53:30.087624+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:30.087014+01:00\\"}"}	unavailable	\N	nochange	62a46f65-f2a1-45ba-b22b-e0faf8479463	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
b1fe10f3-d724-4a38-af30-48d353901be1	deploy	2026-10-23 14:53:30.100471+00	2026-10-23 14:53:30.108568+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:30.107889+01:00\\"}"}	unavailable	\N	nochange	62a46f65-f2a1-45ba-b22b-e0faf8479463	1	{"fs::File[localhost,path=/tmp/test],v=1"}
72569b32-9437-4d13-85bc-f8b321fc7df9	store	2026-10-23 14:53:31.25627+00	2026-10-23 14:53:31.266857+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-23T15:53:31.266880+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2	{"fs::File[localhost,path=/tmp/test],v=2"}
040bcae1-cb15-4e44-8179-ad57ed421ef0	store	2026-10-23 14:53:32.521361+00	2026-10-23 14:53:32.530817+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-23T15:53:32.530851+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
98d0cc19-495f-4624-8b9e-659079bdfb13	deploy	2026-10-23 14:53:32.663088+00	2026-10-23 14:53:32.680098+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-23T15:53:32.678747+01:00\\"}"}	unavailable	\N	nochange	af3a3d3d-b09a-4aec-a667-e0cf08639caa	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
e46a6230-4001-46e7-b0aa-7c9973025fc7	store	2026-10-23 14:53:33.872782+00	2026-10-23 14:53:33.890284+00	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-23T15:53:33.890323+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	4	{"fs::File[localhost,path=/tmp/test],v=4"}
4819fc91-551b-4827-9647-b4e2b4e6ae5f	store	2026-10-23 14:53:35.188326+00	2026-10-23 14:53:35.19553+00	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-23T15:53:35.195563+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	5	{"fs::File[localhost,path=/tmp/test],v=5"}
dc0d5af7-5ad3-4fb1-b717-507e5db63623	store	2026-10-23 14:53:39.688018+00	2026-10-23 14:53:39.69304+00	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-23T15:53:39.693054+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	6	{"fs::File[localhost,path=/tmp/test],v=6"}
8b312258-1102-4284-a2fa-4fc8b97e4d6c	store	2026-10-23 14:53:39.865065+00	2026-10-23 14:53:39.869801+00	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-23T15:53:39.869813+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	{"test::Resource[agent3,key=key3],v=7","test::Resource[agent2,key=key2],v=7","fs::File[localhost,path=/tmp/test],v=7"}
42a1d4ff-effd-4d65-9f38-c83be9b37858	deploy	2026-10-23 14:53:39.918778+00	2026-10-23 14:53:39.940677+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-23T15:53:39.939157+01:00\\"}"}	unavailable	\N	nochange	af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	{"test::Resource[agent2,key=key2],v=7"}
2cc44031-be31-4d95-beee-671bd797b1b7	deploy	2026-10-23 14:53:39.940833+00	2026-10-23 14:53:39.954535+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-23T15:53:39.952353+01:00\\"}"}	unavailable	\N	nochange	af3a3d3d-b09a-4aec-a667-e0cf08639caa	7	{"test::Resource[agent3,key=key3],v=7"}
0557b394-96c7-41fc-9708-8f217f77f95b	store	2026-10-23 14:53:40.04567+00	2026-10-23 14:53:40.049236+00	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-23T15:53:40.049249+01:00\\"}"}	\N	\N	\N	af3a3d3d-b09a-4aec-a667-e0cf08639caa	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
89ef048f-c70c-46e9-9360-f9bef4aa1930	store	2026-10-23 14:53:40.285287+00	2026-10-23 14:53:40.298795+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-23T15:53:40.298809+01:00\\"}"}	\N	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1"}
9957efd8-c300-46b4-b037-f5e9bd481e02	deploy	2026-10-23 14:53:40.32828+00	2026-10-23 14:53:40.345054+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 60fb7ea7-7e32-4893-bce7-19ddff2890c5).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"60fb7ea7-7e32-4893-bce7-19ddff2890c5\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.340572+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/jp/Inmanta/research/dryrun-filtered-background-2026-10-23/core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/jp/Inmanta/research/dryrun-filtered-background-2026-10-23/core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.343044+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 60fb7ea7-7e32-4893-bce7-19ddff2890c5) - duration: 0.0041 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.004146099090576172, \\"deploy_id\\": \\"60fb7ea7-7e32-4893-bce7-19ddff2890c5\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.344931+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Fail[agent1,key=key2],v=1"}
9eff33d3-360f-4755-8fe0-1f6fccde50a2	deploy	2026-10-23 14:53:40.359591+00	2026-10-23 14:53:40.388034+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 523fc0af-3411-46a7-99e8-174485cc4c1c).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"523fc0af-3411-46a7-99e8-174485cc4c1c\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.371734+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 523fc0af-3411-46a7-99e8-174485cc4c1c) - duration: 0.0161 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.01608562469482422, \\"deploy_id\\": \\"523fc0af-3411-46a7-99e8-174485cc4c1c\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.387961+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key1],v=1"}
a0cdbe2a-d5cb-4039-8a89-edcc10b117b0	deploy	2026-10-23 14:53:40.39791+00	2026-10-23 14:53:40.425085+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2da98782-7bc8-4e28-aa53-296f80893111).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"2da98782-7bc8-4e28-aa53-296f80893111\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.408609+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 2da98782-7bc8-4e28-aa53-296f80893111) - duration: 0.0161 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.016117095947265625, \\"deploy_id\\": \\"2da98782-7bc8-4e28-aa53-296f80893111\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.424947+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key6],v=1"}
10f135e5-9978-42df-8f12-a9545a2ab9cb	deploy	2026-10-23 14:53:40.437471+00	2026-10-23 14:53:40.449411+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 0bbfe8d5-1960-4861-be11-53c3638d1d3d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"0bbfe8d5-1960-4861-be11-53c3638d1d3d\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.448569+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.448873+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 0bbfe8d5-1960-4861-be11-53c3638d1d3d) - duration: 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0005285739898681641, \\"deploy_id\\": \\"0bbfe8d5-1960-4861-be11-53c3638d1d3d\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.449300+01:00\\"}"}	skipped	\N	nochange	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key3],v=1"}
d7ca5277-c963-42bd-945e-1ac054a56e2d	dryrun	2026-10-23 14:53:40.605986+00	2026-10-23 14:53:40.607364+00	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.606118+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061 - duration 0.0010 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0009815692901611328, \\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.607297+01:00\\"}"}	dry	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Fail[agent1,key=key2],v=1"}
67c7bdf0-7995-4a5a-a351-fee1fa6a0299	dryrun	2026-10-23 14:53:40.6531+00	2026-10-23 14:53:40.653737+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.653270+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002980232238769531, \\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.653697+01:00\\"}"}	dry	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key1],v=1"}
c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	store	2026-10-23 14:53:40.650399+00	2026-10-23 14:53:40.658216+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-23T15:53:40.658235+01:00\\"}"}	\N	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	{"test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key9],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key11],v=2"}
5d47b99e-479d-44f4-8bd6-330bbbf1a1c9	dryrun	2026-10-23 14:53:40.838116+00	2026-10-23 14:53:40.839067+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.838364+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0004894733428955078, \\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.839012+01:00\\"}"}	dry	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key5],v=1"}
3ff8bbf3-5be9-4e6e-b977-4abd9f162911	dryrun	2026-10-23 14:53:40.852127+00	2026-10-23 14:53:40.852859+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.852318+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00039005279541015625, \\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.852826+01:00\\"}"}	dry	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key6],v=1"}
d229028a-f252-4b7e-afc3-b3ace27a6ef6	dryrun	2026-10-23 14:53:40.677653+00	2026-10-23 14:53:40.678411+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.677771+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 4cbededf-73e6-49ca-a9ce-3c4c25267061 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005209445953369141, \\"dry_run_id\\": \\"4cbededf-73e6-49ca-a9ce-3c4c25267061\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.678381+01:00\\"}"}	dry	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	1	{"test::Resource[agent1,key=key3],v=1"}
d748fbdc-ebcd-43ec-afce-ba2dfdf642a1	deploy	2026-10-23 14:53:40.709202+00	2026-10-23 14:53:40.72447+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 92b990b7-daab-4618-87b1-fdab7546e6df).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"92b990b7-daab-4618-87b1-fdab7546e6df\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.718807+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 92b990b7-daab-4618-87b1-fdab7546e6df) - duration: 0.0055 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.005486011505126953, \\"deploy_id\\": \\"92b990b7-daab-4618-87b1-fdab7546e6df\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.724408+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	{"test::Resource[agent1,key=key9],v=2"}
df3484bf-29cb-4013-86a0-e90e47226953	deploy	2026-10-23 14:53:40.734117+00	2026-10-23 14:53:40.756301+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ce04dfc0-4a4d-4386-a092-bcf83f32a5da).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"ce04dfc0-4a4d-4386-a092-bcf83f32a5da\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.745871+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: ce04dfc0-4a4d-4386-a092-bcf83f32a5da) - duration: 0.0101 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.010137796401977539, \\"deploy_id\\": \\"ce04dfc0-4a4d-4386-a092-bcf83f32a5da\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.756191+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	{"test::Resource[agent1,key=key7],v=2"}
680b82e3-3294-4b44-9bb5-b042fd0747c0	deploy	2026-10-23 14:53:40.765478+00	2026-10-23 14:53:40.78482+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f0d6599c-06b6-497c-a6c5-02624fa0d697).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"f0d6599c-06b6-497c-a6c5-02624fa0d697\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.775111+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.775673+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: f0d6599c-06b6-497c-a6c5-02624fa0d697) - duration: 0.0095 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.009474039077758789, \\"deploy_id\\": \\"f0d6599c-06b6-497c-a6c5-02624fa0d697\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.784736+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	{"test::Resource[agent1,key=key10],v=2"}
23d8a063-45d8-456a-ad14-6a64c50b3dfe	deploy	2026-10-23 14:53:40.797042+00	2026-10-23 14:53:40.82364+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: e1c26f94-c4b2-46e8-8370-ca3e73921581).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"e1c26f94-c4b2-46e8-8370-ca3e73921581\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.809349+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.809830+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: e1c26f94-c4b2-46e8-8370-ca3e73921581) - duration: 0.0141 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.01406550407409668, \\"deploy_id\\": \\"e1c26f94-c4b2-46e8-8370-ca3e73921581\\"}, \\"timestamp\\": \\"2026-10-23T15:53:40.823560+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2	{"test::Resource[agent1,key=key11],v=2"}
ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	store	2026-10-23 14:53:40.980381+00	2026-10-23 14:53:40.99101+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-23T15:53:40.991039+01:00\\"}"}	\N	\N	\N	a4cd0d2c-623c-4219-99c1-d21764b8c9af	3	{"test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key4],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
af3a3d3d-b09a-4aec-a667-e0cf08639caa	a42c9fc5-ba3c-41b8-bb2b-004e9982e8ea	fs::File[localhost,path=/tmp/test]	1
af3a3d3d-b09a-4aec-a667-e0cf08639caa	23c51aed-b2e1-4c72-9129-d49718208e01	fs::File[localhost,path=/tmp/test]	1
62a46f65-f2a1-45ba-b22b-e0faf8479463	2485dfe6-2b27-4216-83ac-1bf11c2f361d	fs::File[localhost,path=/tmp/test]	1
62a46f65-f2a1-45ba-b22b-e0faf8479463	2485dfe6-2b27-4216-83ac-1bf11c2f361d	std::AgentConfig[internal,agentname=localhost]	1
62a46f65-f2a1-45ba-b22b-e0faf8479463	62788570-f54e-4fdc-a420-681f4799c990	std::AgentConfig[internal,agentname=localhost]	1
62a46f65-f2a1-45ba-b22b-e0faf8479463	b1fe10f3-d724-4a38-af30-48d353901be1	fs::File[localhost,path=/tmp/test]	1
af3a3d3d-b09a-4aec-a667-e0cf08639caa	72569b32-9437-4d13-85bc-f8b321fc7df9	fs::File[localhost,path=/tmp/test]	2
af3a3d3d-b09a-4aec-a667-e0cf08639caa	040bcae1-cb15-4e44-8179-ad57ed421ef0	fs::File[localhost,path=/tmp/test]	3
af3a3d3d-b09a-4aec-a667-e0cf08639caa	040bcae1-cb15-4e44-8179-ad57ed421ef0	fs::File[localhost,path=/tmp/test_orphan]	3
af3a3d3d-b09a-4aec-a667-e0cf08639caa	98d0cc19-495f-4624-8b9e-659079bdfb13	fs::File[localhost,path=/tmp/test_orphan]	3
af3a3d3d-b09a-4aec-a667-e0cf08639caa	e46a6230-4001-46e7-b0aa-7c9973025fc7	fs::File[localhost,path=/tmp/test]	4
af3a3d3d-b09a-4aec-a667-e0cf08639caa	4819fc91-551b-4827-9647-b4e2b4e6ae5f	fs::File[localhost,path=/tmp/test]	5
af3a3d3d-b09a-4aec-a667-e0cf08639caa	dc0d5af7-5ad3-4fb1-b717-507e5db63623	fs::File[localhost,path=/tmp/test]	6
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8b312258-1102-4284-a2fa-4fc8b97e4d6c	test::Resource[agent3,key=key3]	7
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8b312258-1102-4284-a2fa-4fc8b97e4d6c	test::Resource[agent2,key=key2]	7
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8b312258-1102-4284-a2fa-4fc8b97e4d6c	fs::File[localhost,path=/tmp/test]	7
af3a3d3d-b09a-4aec-a667-e0cf08639caa	42a1d4ff-effd-4d65-9f38-c83be9b37858	test::Resource[agent2,key=key2]	7
af3a3d3d-b09a-4aec-a667-e0cf08639caa	2cc44031-be31-4d95-beee-671bd797b1b7	test::Resource[agent3,key=key3]	7
af3a3d3d-b09a-4aec-a667-e0cf08639caa	0557b394-96c7-41fc-9708-8f217f77f95b	fs::File[localhost,path=/tmp/test]	8
af3a3d3d-b09a-4aec-a667-e0cf08639caa	0557b394-96c7-41fc-9708-8f217f77f95b	test::Resource[agent2,key=key2]	8
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Resource[agent1,key=key4]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Resource[agent1,key=key3]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Resource[agent1,key=key1]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Resource[agent1,key=key6]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Resource[agent1,key=key5]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	89ef048f-c70c-46e9-9360-f9bef4aa1930	test::Fail[agent1,key=key2]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	9957efd8-c300-46b4-b037-f5e9bd481e02	test::Fail[agent1,key=key2]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	9eff33d3-360f-4755-8fe0-1f6fccde50a2	test::Resource[agent1,key=key1]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	a0cdbe2a-d5cb-4039-8a89-edcc10b117b0	test::Resource[agent1,key=key6]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	10f135e5-9978-42df-8f12-a9545a2ab9cb	test::Resource[agent1,key=key3]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	d7ca5277-c963-42bd-945e-1ac054a56e2d	test::Fail[agent1,key=key2]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key7]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key9]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Fail[agent1,key=key2]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key5]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key10]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key3]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key4]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key1]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	c08cb8ec-ac7a-4dd0-ac9d-c7b1e60ed127	test::Resource[agent1,key=key11]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	67c7bdf0-7995-4a5a-a351-fee1fa6a0299	test::Resource[agent1,key=key1]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	d229028a-f252-4b7e-afc3-b3ace27a6ef6	test::Resource[agent1,key=key3]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	d748fbdc-ebcd-43ec-afce-ba2dfdf642a1	test::Resource[agent1,key=key9]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	df3484bf-29cb-4013-86a0-e90e47226953	test::Resource[agent1,key=key7]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	680b82e3-3294-4b44-9bb5-b042fd0747c0	test::Resource[agent1,key=key10]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	23d8a063-45d8-456a-ad14-6a64c50b3dfe	test::Resource[agent1,key=key11]	2
a4cd0d2c-623c-4219-99c1-d21764b8c9af	5d47b99e-479d-44f4-8bd6-330bbbf1a1c9	test::Resource[agent1,key=key5]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	3ff8bbf3-5be9-4e6e-b977-4abd9f162911	test::Resource[agent1,key=key6]	1
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key7]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key4]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Fail[agent1,key=key2]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key1]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key5]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key8]	3
a4cd0d2c-623c-4219-99c1-d21764b8c9af	ce1b3c74-3f9b-46cb-9aab-3f57c40ebcfc	test::Resource[agent1,key=key3]	3
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
62a46f65-f2a1-45ba-b22b-e0faf8479463	1
af3a3d3d-b09a-4aec-a667-e0cf08639caa	8
a4cd0d2c-623c-4219-99c1-d21764b8c9af	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
NOSdrive	af3a3d3d-b09a-4aec-a667-e0cf08639caa	2026-10-23 14:53:17.462692+00	\N	58efea03-8be1-4050-b91e-5b5a28928ca8
NOSdrive	62a46f65-f2a1-45ba-b22b-e0faf8479463	2026-10-23 14:53:17.607725+00	\N	ab6f088c-0389-428b-8ec7-3a52a58670aa
NOSdrive	a4cd0d2c-623c-4219-99c1-d21764b8c9af	2026-10-23 14:53:40.12242+00	2026-10-23 14:53:40.94964+00	79868d4c-979d-41e2-8b4b-e3dfb39c0706
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610230}
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

--\unrestrict 0PzVM3p5UDIUpnHW8pWO9Za1DNY1ccIuAane8WaUv0phJY6H2cOJL0t91p28MxD

