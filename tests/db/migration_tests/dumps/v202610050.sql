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
00e40893-72fb-4684-b14d-61be833dfab4	$__scheduler	f	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	$__scheduler	f	\N
3ac32925-91d7-4d12-a723-dc9dbd865260	$__scheduler	f	\N
00e40893-72fb-4684-b14d-61be833dfab4	localhost	f	\N
00e40893-72fb-4684-b14d-61be833dfab4	internal	f	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	localhost	f	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	internal	f	\N
00e40893-72fb-4684-b14d-61be833dfab4	agent2	f	\N
00e40893-72fb-4684-b14d-61be833dfab4	agent3	f	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	agent1	t	t
05c96281-a126-4337-9638-1bfbc3b14d5c	$__scheduler	t	t
75d38996-0b8a-4ed1-9d1d-0651e2b5a840	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
1	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
1	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
1	internal	std	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb
1	localhost	fs	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb
2	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
2	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
2	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
3	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
3	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
3	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
4	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
4	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
4	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
5	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
5	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
5	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
6	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
6	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
6	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
7	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
7	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
7	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
8	localhost	fs	00e40893-72fb-4684-b14d-61be833dfab4
8	internal	std	00e40893-72fb-4684-b14d-61be833dfab4
8	localhost	std	00e40893-72fb-4684-b14d-61be833dfab4
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
550c55fe-7d2f-43e3-8c41-9d345c39317c	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:30:57.387315+02	2026-10-05 08:31:14.184309+02	2026-10-05 08:30:57.369465+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	6b7599c5-ab0b-4f7d-8911-89a112fb6a9c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
e1424d63-1f5e-4fb3-92c8-18a0b577fb3c	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	2026-10-05 08:31:14.38446+02	2026-10-05 08:31:29.405966+02	2026-10-05 08:31:14.368023+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	53dde437-c1e8-4311-b4b0-5d3f7852e123	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
736727e2-a05a-417c-895e-57d06a83ef31	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:29.586319+02	2026-10-05 08:31:30.599762+02	2026-10-05 08:31:29.571372+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	e7622b73-d841-4814-ae1f-3e084bee1877	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
10f0c7e2-9cea-4253-93e3-db35389f0317	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:30.704331+02	2026-10-05 08:31:31.666699+02	2026-10-05 08:31:30.636199+02	{}	{"add_one_resource": "true"}	t	f	t	3	3a06d363-dca6-469d-a7ea-902f24dfe91a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
c34c9d86-ca22-4e14-8f32-eb77051d3a02	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:31.838652+02	2026-10-05 08:31:32.773613+02	2026-10-05 08:31:31.822398+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	fdc3af98-a25a-41e6-8f7b-f5a6a8bd199e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
2fca0224-883a-4dea-b13c-551213a68a09	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:32.979091+02	2026-10-05 08:31:33.933012+02	2026-10-05 08:31:32.976018+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	43a5e564-9d6c-4876-b73d-802973bbe309	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
78c6343c-8566-4ae0-97d1-a96b8d97eb00	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:34.106332+02	2026-10-05 08:31:46.633709+02	2026-10-05 08:31:34.094396+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	d3dd1de9-d560-4fba-87b9-f66dbf7bab4a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bc8abf08-8aa2-4048-b006-d8a0ec3c52fc	75d38996-0b8a-4ed1-9d1d-0651e2b5a840	2026-10-05 08:31:47.348339+02	2026-10-05 08:31:47.350148+02	2026-10-05 08:31:47.344916+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	e1664ec1-4b2d-48e3-acf4-f340d0c71fde	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:14.165108+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:46.811228+02	t	\N	3	{}	{}	7	t	\N	\N
1	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	2026-10-05 08:31:29.392821+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:30.582848+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:31.657871+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:32.765014+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:33.924348+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:46.620308+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	05c96281-a126-4337-9638-1bfbc3b14d5c	2026-10-05 08:31:46.969566+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:31:46.660663+02	t	\N	4	{}	{}	6	t	\N	\N
2	05c96281-a126-4337-9638-1bfbc3b14d5c	2026-10-05 08:31:47.103996+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	05c96281-a126-4337-9638-1bfbc3b14d5c	2026-10-05 08:31:47.230004+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	1	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	1	fs	1.2.0
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	std	7.0.0
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	2	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	2	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	3	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	3	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	4	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	4	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	5	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	5	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	6	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	6	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	7	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	7	std	8.7.4
00e40893-72fb-4684-b14d-61be833dfab4	8	fs	1.2.0
00e40893-72fb-4684-b14d-61be833dfab4	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	discovery::Discovered[myagent,name=discovered]	{}	2026-10-05 08:31:47.233728+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
00e40893-72fb-4684-b14d-61be833dfab4	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-05 08:31:47.233749+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
772ae82e-018b-40ef-8b08-9dec87cd0d89	05c96281-a126-4337-9638-1bfbc3b14d5c	1	2026-10-05 08:31:47.090339+02	6	0	{"18c2ada0-568f-50bc-92c8-6137d33b562d": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "2aa6fd20-e9e4-58f3-af64-17a449e2b2ad": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {"handler": {"current": "FAILED", "desired": "Unable to construct an executor for this resource"}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "480cc96d-2459-5184-a12e-0bca6a97dbec": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"handler": {"current": "FAILED", "desired": "Unable to construct an executor for this resource"}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "71d00c5c-d5d2-5d7f-9676-694eb364d30e": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "b2a42da9-56aa-59f0-9343-01d3e36bc811": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {"handler": {"current": "FAILED", "desired": "Unable to construct an executor for this resource"}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "c2776f1d-dd5b-51a5-888f-eb01eeb794e8": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"handler": {"current": "FAILED", "desired": "Unable to construct an executor for this resource"}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
75d38996-0b8a-4ed1-9d1d-0651e2b5a840	dev-4	b95513dc-80ff-43c0-b926-b66815f62eba			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
00e40893-72fb-4684-b14d-61be833dfab4	dev-1	b95513dc-80ff-43c0-b926-b66815f62eba			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	dev-1-twin	b95513dc-80ff-43c0-b926-b66815f62eba			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
3ac32925-91d7-4d12-a723-dc9dbd865260	dev-2	b95513dc-80ff-43c0-b926-b66815f62eba			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
05c96281-a126-4337-9638-1bfbc3b14d5c	dev-3	b95513dc-80ff-43c0-b926-b66815f62eba			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.4	00e40893-72fb-4684-b14d-61be833dfab4	{}	f
fs	1.2.0	00e40893-72fb-4684-b14d-61be833dfab4	{}	f
std	7.0.0	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	{}	f
fs	1.2.0	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	{}	f
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
97822bf5-c523-46cc-8610-8bca7ea206bf	75d38996-0b8a-4ed1-9d1d-0651e2b5a840	2026-10-05 08:31:47.351546+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/bc8abf08-8aa2-4048-b006-d8a0ec3c52fc	f	f	bc8abf08-8aa2-4048-b006-d8a0ec3c52fc
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
5c039753-21d7-4417-96d3-2a2c2c6da31d	fact1	value1	00e40893-72fb-4684-b14d-61be833dfab4	std::testing::NullResource[localhost,name=test1]	fact	2026-10-05 08:31:32.951912+02	{}	f
25a53513-ec6b-49c1-a1d9-90f7ee68f306	fact2	value2	00e40893-72fb-4684-b14d-61be833dfab4	std::testing::NullResource[localhost,name=test2]	fact	2026-10-05 08:31:32.958653+02	{}	t
5b1c6ee7-5ae8-42cd-8c1b-5703ab72c8fb	fact3	value3	00e40893-72fb-4684-b14d-61be833dfab4	std::testing::NullResource[localhost,name=test3]	fact	2026-10-05 08:31:32.962817+02	{}	t
cf199dfd-958f-46e4-91f8-5fa3abfaec60	parameter1	value1	00e40893-72fb-4684-b14d-61be833dfab4		fact	2026-10-05 08:31:32.969758+02	{}	f
c67d4f99-522f-4081-85b6-8f60873b1449	parameter2	value2	00e40893-72fb-4684-b14d-61be833dfab4		fact	2026-10-05 08:31:32.971943+02	{}	f
5400c88b-aa21-47c2-b7fd-fe22d39a36f4	parameter3	value3	00e40893-72fb-4684-b14d-61be833dfab4		fact	2026-10-05 08:31:32.97413+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
b95513dc-80ff-43c0-b926-b66815f62eba	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
06ca4272-0cda-404a-b6e3-fa80e7521c1b	2026-10-05 08:30:57.388143+02	2026-10-05 08:30:57.39263+02		Init		Using extra environment variables during compile \n	0	550c55fe-7d2f-43e3-8c41-9d345c39317c
83634f46-b02f-4fce-88cc-fc5ade27c1d5	2026-10-05 08:30:57.393753+02	2026-10-05 08:30:57.415657+02		Venv check		Creating new venv at /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env-py3.14\n	0	550c55fe-7d2f-43e3-8c41-9d345c39317c
b089bc5f-9a5d-4dda-8fea-4291278a6ef9	2026-10-05 08:30:57.41832+02	2026-10-05 08:30:57.781284+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	550c55fe-7d2f-43e3-8c41-9d345c39317c
37a77af2-9bb3-4239-8e93-ce0adcb96f56	2026-10-05 08:30:57.782079+02	2026-10-05 08:31:13.223345+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp_93jtmf4:\n                                 Pip command: /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp_93jtmf4 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<51,>=36 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64.whl (4.8 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pyjwt-2.15.1-py3-none-any.whl (33 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Collecting setproctitle~=1.3 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached setproctitle-1.3.8-cp314-cp314-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (33 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.6/4.6 MB 37.8 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Collecting MarkupSafe>=2.0 (from jinja2~=3.0->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading markupsafe-3.0.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (23 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading strawberry_graphql-0.331.1-py3-none-any.whl (355 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Collecting charset_normalizer<4,>=2 (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached charset_normalizer-3.5.2-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (255 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.4)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading tzdata-2026.5-py2.py3-none-any.whl (347 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tzdata, SQLAlchemy, setproctitle, PyJWT, mitogen, MarkupSafe, charset_normalizer, strawberry-graphql, cryptography, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.4\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.1\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: setproctitle\ninmanta.pip              DEBUG   Found existing installation: setproctitle 1.3.7\ninmanta.pip              DEBUG   Not uninstalling setproctitle at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'setproctitle'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.15.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: MarkupSafe\ninmanta.pip              DEBUG   Found existing installation: MarkupSafe 3.0.3\ninmanta.pip              DEBUG   Not uninstalling markupsafe at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'MarkupSafe'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: charset_normalizer\ninmanta.pip              DEBUG   Found existing installation: charset-normalizer 3.5.1\ninmanta.pip              DEBUG   Not uninstalling charset-normalizer at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.327.7\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 50.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed MarkupSafe-3.0.4 PyJWT-2.15.1 SQLAlchemy-2.1.3 charset_normalizer-3.5.2 cryptography-50.0.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53 setproctitle-1.3.8 strawberry-graphql-0.331.1 tzdata-2026.5\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	550c55fe-7d2f-43e3-8c41-9d345c39317c
2c8fb723-a1e4-40b8-aca8-3c989d79615b	2026-10-05 08:31:29.58782+02	2026-10-05 08:31:29.595065+02		Init		Using extra environment variables during compile \n	0	736727e2-a05a-417c-895e-57d06a83ef31
4d62b1fe-4bc1-4cfc-9c3d-9af3e6119b1d	2026-10-05 08:31:29.596137+02	2026-10-05 08:31:29.598423+02		Venv check		Found existing venv\n	0	736727e2-a05a-417c-895e-57d06a83ef31
76772c2c-a8fa-4ff3-bfde-1c19d30836c2	2026-10-05 08:31:14.399361+02	2026-10-05 08:31:14.682124+02	/tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e1424d63-1f5e-4fb3-92c8-18a0b577fb3c
b9975ba6-1451-4349-86ce-58a7c7e5ece7	2026-10-05 08:31:13.22434+02	2026-10-05 08:31:14.183643+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpliz0sbmz --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.018 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.023 seconds\ncompiler       DEBUG   The entire export command took 0.072 seconds\n	0	550c55fe-7d2f-43e3-8c41-9d345c39317c
623c5dd4-1360-4bf1-aae9-d94da3e63dfc	2026-10-05 08:31:14.384822+02	2026-10-05 08:31:14.386767+02		Init		Using extra environment variables during compile \n	0	e1424d63-1f5e-4fb3-92c8-18a0b577fb3c
2af8a1c4-0efa-4f13-a761-339d920f1239	2026-10-05 08:31:14.386987+02	2026-10-05 08:31:14.397723+02		Venv check		Creating new venv at /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env-py3.14\n	0	e1424d63-1f5e-4fb3-92c8-18a0b577fb3c
a0fdccbf-45d8-4a4c-b755-7900b650c521	2026-10-05 08:31:14.682947+02	2026-10-05 08:31:28.475711+02	/tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpmph_3dfu:\n                                 Pip command: /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpmph_3dfu inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Collecting cryptography<51,>=36 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64.whl (4.8 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.0)\ninmanta.pip              DEBUG   Collecting PyJWT~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pyjwt-2.15.1-py3-none-any.whl (33 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Collecting setproctitle~=1.3 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached setproctitle-1.3.8-cp314-cp314-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (33 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Collecting MarkupSafe>=2.0 (from jinja2~=3.0->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached markupsafe-3.0.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (23 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.331.1-py3-none-any.whl (355 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Collecting charset_normalizer<4,>=2 (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached charset_normalizer-3.5.2-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (255 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.4)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tzdata-2026.5-py2.py3-none-any.whl (347 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: tzdata, SQLAlchemy, setproctitle, PyJWT, mitogen, MarkupSafe, charset_normalizer, strawberry-graphql, cryptography, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.4\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.1\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: setproctitle\ninmanta.pip              DEBUG   Found existing installation: setproctitle 1.3.7\ninmanta.pip              DEBUG   Not uninstalling setproctitle at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'setproctitle'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: PyJWT\ninmanta.pip              DEBUG   Found existing installation: PyJWT 2.15.0\ninmanta.pip              DEBUG   Not uninstalling pyjwt at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'PyJWT'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: MarkupSafe\ninmanta.pip              DEBUG   Found existing installation: MarkupSafe 3.0.3\ninmanta.pip              DEBUG   Not uninstalling markupsafe at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'MarkupSafe'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: charset_normalizer\ninmanta.pip              DEBUG   Found existing installation: charset-normalizer 3.5.1\ninmanta.pip              DEBUG   Not uninstalling charset-normalizer at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'charset-normalizer'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.327.7\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 50.0.1\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed MarkupSafe-3.0.4 PyJWT-2.15.1 SQLAlchemy-2.1.3 charset_normalizer-3.5.2 cryptography-50.0.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53 setproctitle-1.3.8 strawberry-graphql-0.331.1 tzdata-2026.5\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	e1424d63-1f5e-4fb3-92c8-18a0b577fb3c
3f1591bb-e148-4cf7-a881-90ecd4337540	2026-10-05 08:31:31.840386+02	2026-10-05 08:31:31.845744+02		Init		Using extra environment variables during compile \n	0	c34c9d86-ca22-4e14-8f32-eb77051d3a02
aac13c4e-17ec-4e65-aeb1-3f4903ab712b	2026-10-05 08:31:31.845974+02	2026-10-05 08:31:31.84638+02		Venv check		Found existing venv\n	0	c34c9d86-ca22-4e14-8f32-eb77051d3a02
8dff295a-ed83-40ab-874b-2203680fe62d	2026-10-05 08:31:28.476418+02	2026-10-05 08:31:29.405494+02	/tmp/tmp9ifc5bbj/server/5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpczszf7mq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	e1424d63-1f5e-4fb3-92c8-18a0b577fb3c
687e7cac-7da0-4a6e-839b-d2fa3da25667	2026-10-05 08:31:32.979925+02	2026-10-05 08:31:32.982016+02		Init		Using extra environment variables during compile \n	0	2fca0224-883a-4dea-b13c-551213a68a09
a8ad7a0b-c0b5-4205-83e9-6e40b02b41bd	2026-10-05 08:31:32.982239+02	2026-10-05 08:31:32.98272+02		Venv check		Found existing venv\n	0	2fca0224-883a-4dea-b13c-551213a68a09
31c0c48f-3a6c-4e63-8b80-9d1266b6411c	2026-10-05 08:31:29.59947+02	2026-10-05 08:31:30.599324+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpmsky9zz9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.019 seconds\ncompiler       DEBUG   The entire export command took 0.061 seconds\n	0	736727e2-a05a-417c-895e-57d06a83ef31
111c21a6-d9ba-43fa-8a8a-2c6309aa8e5b	2026-10-05 08:31:30.706387+02	2026-10-05 08:31:30.715297+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	10f0c7e2-9cea-4253-93e3-db35389f0317
5190028b-910f-4e28-a5d2-25e3fba7d378	2026-10-05 08:31:30.716443+02	2026-10-05 08:31:30.718662+02		Venv check		Found existing venv\n	0	10f0c7e2-9cea-4253-93e3-db35389f0317
1d6ef93d-0813-456b-8a5d-bd711bc52d48	2026-10-05 08:31:30.719655+02	2026-10-05 08:31:31.666189+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmppk4up415 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	10f0c7e2-9cea-4253-93e3-db35389f0317
06f95ade-1e41-4312-a0ed-4ea6dfba0a0e	2026-10-05 08:31:31.846553+02	2026-10-05 08:31:32.773172+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpm7q5z_g_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.049 seconds\n	0	c34c9d86-ca22-4e14-8f32-eb77051d3a02
a0c770c5-5a09-409b-900f-8b71a7906ad5	2026-10-05 08:31:34.122527+02	2026-10-05 08:31:34.464531+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	78c6343c-8566-4ae0-97d1-a96b8d97eb00
4f56f196-02f4-493c-b1d9-18603ed9378f	2026-10-05 08:31:32.982936+02	2026-10-05 08:31:33.932507+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1ej2vvu2 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	2fca0224-883a-4dea-b13c-551213a68a09
0539d4f8-9ec6-4da4-b7ed-289e042a743d	2026-10-05 08:31:34.109277+02	2026-10-05 08:31:34.115937+02		Init		Using extra environment variables during compile \n	0	78c6343c-8566-4ae0-97d1-a96b8d97eb00
feeebe86-f1a8-4ee0-9a89-27b96a9057be	2026-10-05 08:31:34.116786+02	2026-10-05 08:31:34.118645+02		Venv check		Found existing venv\n	0	78c6343c-8566-4ae0-97d1-a96b8d97eb00
cd05d215-1f28-4e69-8f4b-fc057dcbade7	2026-10-05 08:31:47.348669+02	2026-10-05 08:31:47.349868+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp9ifc5bbj/server/75d38996-0b8a-4ed1-9d1d-0651e2b5a840/compiler and no repository set.\n	1	bc8abf08-8aa2-4048-b006-d8a0ec3c52fc
984a143e-928f-4532-a68c-be7e7f07ba0b	2026-10-05 08:31:34.465129+02	2026-10-05 08:31:45.507962+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpdnl4xrlu:\n                                 Pip command: /tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpdnl4xrlu inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in ./.env/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.331.1)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in ./.env/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in ./.env/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	78c6343c-8566-4ae0-97d1-a96b8d97eb00
a43481b8-5be1-4f33-8e66-6ba70c47777c	2026-10-05 08:31:45.508995+02	2026-10-05 08:31:46.632893+02	/tmp/tmp9ifc5bbj/server/00e40893-72fb-4684-b14d-61be833dfab4/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 00e40893-72fb-4684-b14d-61be833dfab4 --server_address localhost --server_port 41965 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_sv86xzo --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.016 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.013 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:41965/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:41965/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.075 seconds\n	0	78c6343c-8566-4ae0-97d1-a96b8d97eb00
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	d8d96212-4de9-4472-82cf-6a00ff5b22a0
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d8d96212-4de9-4472-82cf-6a00ff5b22a0
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	69094d23-412c-49c0-8e98-5dd06e6ae56b
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	69094d23-412c-49c0-8e98-5dd06e6ae56b
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	498d4c4c-b728-4047-b5c6-de0b03d3bdc3
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	498d4c4c-b728-4047-b5c6-de0b03d3bdc3
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	db68f327-8219-4c60-aeb4-1809acc9bb0b
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	db68f327-8219-4c60-aeb4-1809acc9bb0b
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	db68f327-8219-4c60-aeb4-1809acc9bb0b
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	f71d599c-12c5-4daa-9162-3341595c1969
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	f71d599c-12c5-4daa-9162-3341595c1969
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	d61c0542-83f4-4faa-a97b-8c11d2b7e576
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d61c0542-83f4-4faa-a97b-8c11d2b7e576
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	4298bc5f-983d-4a26-b429-1d691516c45d
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	4298bc5f-983d-4a26-b429-1d691516c45d
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	24c33fbd-aa71-4b3c-9a0c-f910b48e9c68
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	24c33fbd-aa71-4b3c-9a0c-f910b48e9c68
00e40893-72fb-4684-b14d-61be833dfab4	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	524c73ae-ec44-4f24-805c-502c860d14b1
00e40893-72fb-4684-b14d-61be833dfab4	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	44ef7260-1f10-4855-85cd-d4018d8b9e3c
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	7cec2fb0-854c-42be-8fe0-99280d865e1e
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7cec2fb0-854c-42be-8fe0-99280d865e1e
00e40893-72fb-4684-b14d-61be833dfab4	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	515e0fbd-431e-493e-be95-02a6bba9de44
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	fc8cdc31-3551-46ea-9282-77ca23c34ee5
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key10]	2026-10-05 08:31:47.120549+02	\N	2026-10-05 08:31:47.120549+02	a060d3943ce7843d7df5937d47b21669	2	unavailable	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:47.108215+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-05 08:31:46.9736+02	\N	\N	\N
00e40893-72fb-4684-b14d-61be833dfab4	std::AgentConfig[internal,agentname=localhost]	2026-10-05 08:31:14.248718+02	\N	2026-10-05 08:31:14.248718+02	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:14.232545+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key7]	2026-10-05 08:31:47.123451+02	\N	2026-10-05 08:31:47.123451+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	unavailable	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:47.108215+02	f	\N	\N
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test]	2026-10-05 08:31:14.253984+02	\N	2026-10-05 08:31:14.253984+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:14.232545+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-05 08:31:46.9736+02	\N	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key11]	2026-10-05 08:31:47.126174+02	\N	2026-10-05 08:31:47.126174+02	c31940c3067584e6fcf87bcd660834be	2	unavailable	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:47.108215+02	f	\N	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	std::AgentConfig[internal,agentname=localhost]	2026-10-05 08:31:29.446486+02	\N	2026-10-05 08:31:29.446486+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:29.438358+02	f	\N	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	fs::File[localhost,path=/tmp/test]	2026-10-05 08:31:29.450352+02	\N	2026-10-05 08:31:29.450352+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:29.438358+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Fail[agent1,key=key2]	2026-10-05 08:31:46.984805+02	\N	2026-10-05 08:31:46.984805+02	fa7087083326c953261c388f13f3df3c	1	unavailable	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.9736+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key9]	2026-10-05 08:31:47.12894+02	\N	2026-10-05 08:31:47.12894+02	a2101e55beec503a0c2501581a60b24e	2	unavailable	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:47.108215+02	f	\N	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key3]	2026-10-05 08:31:46.987372+02	\N	2026-10-05 08:31:46.987372+02	c455b56fd58fef5ebaa9bb23407c7776	1	unavailable	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.9736+02	f	\N	\N
00e40893-72fb-4684-b14d-61be833dfab4	fs::File[localhost,path=/tmp/test_orphan]	2026-10-05 08:31:31.699061+02	\N	2026-10-05 08:31:31.699061+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:31.693572+02	f	\N	3
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key1]	2026-10-05 08:31:46.989948+02	\N	2026-10-05 08:31:46.989948+02	84b23b0667021387d0c1651fae901e68	1	unavailable	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.9736+02	f	\N	\N
00e40893-72fb-4684-b14d-61be833dfab4	test::Resource[agent2,key=key2]	2026-10-05 08:31:46.70232+02	\N	2026-10-05 08:31:46.70232+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.692432+02	f	\N	\N
00e40893-72fb-4684-b14d-61be833dfab4	test::Resource[agent3,key=key3]	2026-10-05 08:31:46.700579+02	\N	2026-10-05 08:31:46.700579+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.692432+02	f	\N	7
05c96281-a126-4337-9638-1bfbc3b14d5c	test::Resource[agent1,key=key6]	2026-10-05 08:31:46.981199+02	\N	2026-10-05 08:31:46.981199+02	e0526e715e0780667151d80df5b87059	1	unavailable	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	FAILED	NOT_BLOCKED	f	2026-10-05 08:31:46.9736+02	f	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	d8d96212-4de9-4472-82cf-6a00ff5b22a0	\N
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	69094d23-412c-49c0-8e98-5dd06e6ae56b	\N
00e40893-72fb-4684-b14d-61be833dfab4	498d4c4c-b728-4047-b5c6-de0b03d3bdc3	\N
00e40893-72fb-4684-b14d-61be833dfab4	db68f327-8219-4c60-aeb4-1809acc9bb0b	\N
00e40893-72fb-4684-b14d-61be833dfab4	f71d599c-12c5-4daa-9162-3341595c1969	\N
00e40893-72fb-4684-b14d-61be833dfab4	d61c0542-83f4-4faa-a97b-8c11d2b7e576	\N
00e40893-72fb-4684-b14d-61be833dfab4	4298bc5f-983d-4a26-b429-1d691516c45d	\N
00e40893-72fb-4684-b14d-61be833dfab4	24c33fbd-aa71-4b3c-9a0c-f910b48e9c68	\N
00e40893-72fb-4684-b14d-61be833dfab4	524c73ae-ec44-4f24-805c-502c860d14b1	set-b
00e40893-72fb-4684-b14d-61be833dfab4	44ef7260-1f10-4855-85cd-d4018d8b9e3c	set-a
00e40893-72fb-4684-b14d-61be833dfab4	7cec2fb0-854c-42be-8fe0-99280d865e1e	\N
00e40893-72fb-4684-b14d-61be833dfab4	515e0fbd-431e-493e-be95-02a6bba9de44	set-a
05c96281-a126-4337-9638-1bfbc3b14d5c	33e939a8-bd5c-49a4-a381-7e35067375c6	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	5c99d372-7cb0-43d5-931c-1de186aabdab	\N
05c96281-a126-4337-9638-1bfbc3b14d5c	fc8cdc31-3551-46ea-9282-77ca23c34ee5	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	1	d8d96212-4de9-4472-82cf-6a00ff5b22a0
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	69094d23-412c-49c0-8e98-5dd06e6ae56b
00e40893-72fb-4684-b14d-61be833dfab4	2	498d4c4c-b728-4047-b5c6-de0b03d3bdc3
00e40893-72fb-4684-b14d-61be833dfab4	3	db68f327-8219-4c60-aeb4-1809acc9bb0b
00e40893-72fb-4684-b14d-61be833dfab4	4	f71d599c-12c5-4daa-9162-3341595c1969
00e40893-72fb-4684-b14d-61be833dfab4	5	d61c0542-83f4-4faa-a97b-8c11d2b7e576
00e40893-72fb-4684-b14d-61be833dfab4	6	4298bc5f-983d-4a26-b429-1d691516c45d
00e40893-72fb-4684-b14d-61be833dfab4	7	24c33fbd-aa71-4b3c-9a0c-f910b48e9c68
00e40893-72fb-4684-b14d-61be833dfab4	7	524c73ae-ec44-4f24-805c-502c860d14b1
00e40893-72fb-4684-b14d-61be833dfab4	7	44ef7260-1f10-4855-85cd-d4018d8b9e3c
00e40893-72fb-4684-b14d-61be833dfab4	8	7cec2fb0-854c-42be-8fe0-99280d865e1e
00e40893-72fb-4684-b14d-61be833dfab4	8	515e0fbd-431e-493e-be95-02a6bba9de44
05c96281-a126-4337-9638-1bfbc3b14d5c	1	33e939a8-bd5c-49a4-a381-7e35067375c6
05c96281-a126-4337-9638-1bfbc3b14d5c	2	5c99d372-7cb0-43d5-931c-1de186aabdab
05c96281-a126-4337-9638-1bfbc3b14d5c	3	fc8cdc31-3551-46ea-9282-77ca23c34ee5
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a5691886-c77f-4c41-ab7c-f4372aa4f8db	store	2026-10-05 08:31:14.16505+02	2026-10-05 08:31:14.17228+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T08:31:14.172293+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
0786e121-5116-49dd-8b07-e56289903ce7	deploy	2026-10-05 08:31:14.239748+02	2026-10-05 08:31:14.248718+02	{"{\\"msg\\": \\"All resources of type `std::AgentConfig` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"std::AgentConfig\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:14.248062+02:00\\"}"}	unavailable	\N	nochange	00e40893-72fb-4684-b14d-61be833dfab4	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
6550b904-7f62-4e92-a7cd-3cc792d669d3	deploy	2026-10-05 08:31:14.252527+02	2026-10-05 08:31:14.253984+02	{"{\\"msg\\": \\"All resources of type `fs::File` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"fs::File\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:14.253441+02:00\\"}"}	unavailable	\N	nochange	00e40893-72fb-4684-b14d-61be833dfab4	1	{"fs::File[localhost,path=/tmp/test],v=1"}
89991d16-918d-479f-930e-a37b2e80e2f0	store	2026-10-05 08:31:29.392756+02	2026-10-05 08:31:29.398432+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T08:31:29.398444+02:00\\"}"}	\N	\N	\N	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
7c78a284-6680-4f44-a648-829ef621f06c	deploy	2026-10-05 08:31:29.444697+02	2026-10-05 08:31:29.446486+02	{"{\\"msg\\": \\"All resources of type `std::AgentConfig` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"std::AgentConfig\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:29.445892+02:00\\"}"}	unavailable	\N	nochange	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c828955c-342f-4883-a992-e6115f509a72	deploy	2026-10-05 08:31:29.448915+02	2026-10-05 08:31:29.450352+02	{"{\\"msg\\": \\"All resources of type `fs::File` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"fs::File\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:29.449846+02:00\\"}"}	unavailable	\N	nochange	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1	{"fs::File[localhost,path=/tmp/test],v=1"}
1b563fa2-6883-402e-b357-3bb7db035414	store	2026-10-05 08:31:30.5828+02	2026-10-05 08:31:30.588582+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-05T08:31:30.588590+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
ab7bb0b9-5410-42d6-996f-3bf18dead622	store	2026-10-05 08:31:31.657823+02	2026-10-05 08:31:31.660209+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-05T08:31:31.660217+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
116b1ac8-6b64-4882-80cf-0ac40da57c05	deploy	2026-10-05 08:31:31.696651+02	2026-10-05 08:31:31.699061+02	{"{\\"msg\\": \\"All resources of type `fs::File` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"fs::File\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:31.698475+02:00\\"}"}	unavailable	\N	nochange	00e40893-72fb-4684-b14d-61be833dfab4	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
2b82f1ff-56d1-48e4-bfc3-331fb4ae68e8	store	2026-10-05 08:31:32.764967+02	2026-10-05 08:31:32.767131+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-05T08:31:32.767140+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	4	{"fs::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
97242ebf-c5da-47f4-8cc0-e7786dc79600	store	2026-10-05 08:31:33.924299+02	2026-10-05 08:31:33.926563+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-05T08:31:33.926572+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
d8f930ec-8421-4643-9fe0-4b50f0a83092	store	2026-10-05 08:31:46.620255+02	2026-10-05 08:31:46.622627+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-05T08:31:46.622637+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	6	{"std::AgentConfig[internal,agentname=localhost],v=6","fs::File[localhost,path=/tmp/test],v=6"}
e2062390-ce01-4b44-a497-eeb132e59e86	store	2026-10-05 08:31:46.660561+02	2026-10-05 08:31:46.665311+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-05T08:31:46.665320+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	7	{"test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7","std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7"}
9e613e23-fbc7-400e-9461-5fae7fb68aa8	deploy	2026-10-05 08:31:46.700651+02	2026-10-05 08:31:46.70232+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.701721+02:00\\"}"}	unavailable	\N	nochange	00e40893-72fb-4684-b14d-61be833dfab4	7	{"test::Resource[agent2,key=key2],v=7"}
8ead3253-65af-4665-b083-a8f51f9a544f	deploy	2026-10-05 08:31:46.697971+02	2026-10-05 08:31:46.700579+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.699962+02:00\\"}"}	unavailable	\N	nochange	00e40893-72fb-4684-b14d-61be833dfab4	7	{"test::Resource[agent3,key=key3],v=7"}
b8013e1f-7351-4415-81dd-22ffd88868aa	store	2026-10-05 08:31:46.811132+02	2026-10-05 08:31:46.816517+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-05T08:31:46.816529+02:00\\"}"}	\N	\N	\N	00e40893-72fb-4684-b14d-61be833dfab4	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8","std::AgentConfig[internal,agentname=localhost],v=8"}
77f70c9c-3b5d-42be-8642-6d62d9f23d1e	store	2026-10-05 08:31:46.969511+02	2026-10-05 08:31:46.971408+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-05T08:31:46.971416+02:00\\"}"}	\N	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key1],v=1","test::Fail[agent1,key=key2],v=1"}
d4054ad6-cbd4-451b-a20c-5408783b97fa	dryrun	2026-10-05 08:31:47.112029+02	2026-10-05 08:31:47.11273+02	{}	dry	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key3],v=1"}
b7368636-8b8a-48c3-b177-4b224980dba3	deploy	2026-10-05 08:31:47.118498+02	2026-10-05 08:31:47.120549+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:47.119809+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	2	{"test::Resource[agent1,key=key10],v=2"}
9439e843-d963-4694-8d82-9b90e8d37351	deploy	2026-10-05 08:31:47.12179+02	2026-10-05 08:31:47.123451+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:47.122844+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	2	{"test::Resource[agent1,key=key7],v=2"}
c714a23a-18ef-42bc-97dc-4d11e0b9ee1a	deploy	2026-10-05 08:31:47.124467+02	2026-10-05 08:31:47.126174+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:47.125551+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	2	{"test::Resource[agent1,key=key11],v=2"}
62abfd6f-639b-4fcb-ae83-511ab6dd814c	deploy	2026-10-05 08:31:46.979233+02	2026-10-05 08:31:46.981199+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.980556+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key6],v=1"}
e10b81de-2cb5-47ed-9cd1-5394f944f17c	deploy	2026-10-05 08:31:46.983124+02	2026-10-05 08:31:46.984805+02	{"{\\"msg\\": \\"All resources of type `test::Fail` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Fail\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.984228+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Fail[agent1,key=key2],v=1"}
81f1392d-599d-4d9f-b5ab-f62e7ea370be	deploy	2026-10-05 08:31:46.985805+02	2026-10-05 08:31:46.987372+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.986827+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key3],v=1"}
37f933b8-6e58-4c6f-b163-8a5f26a29a10	deploy	2026-10-05 08:31:46.988314+02	2026-10-05 08:31:46.989948+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:46.989347+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key1],v=1"}
b3771416-e5e1-46ce-9092-19c6fd6cf4a7	dryrun	2026-10-05 08:31:47.093498+02	2026-10-05 08:31:47.094748+02	{}	dry	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Fail[agent1,key=key2],v=1"}
2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	store	2026-10-05 08:31:47.103947+02	2026-10-05 08:31:47.105952+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-05T08:31:47.105960+02:00\\"}"}	\N	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	2	{"test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key11],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key4],v=2"}
c017d44f-92b2-4de5-9843-dbb98b13d989	dryrun	2026-10-05 08:31:47.099874+02	2026-10-05 08:31:47.10059+02	{}	dry	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key1],v=1"}
3ace215d-e03e-446f-b69f-169d3f8f62db	store	2026-10-05 08:31:47.229954+02	2026-10-05 08:31:47.231678+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-05T08:31:47.231686+02:00\\"}"}	\N	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	3	{"test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key5],v=3"}
752ac25d-b68d-4cf0-8e68-b581aa55ee3c	deploy	2026-10-05 08:31:47.127248+02	2026-10-05 08:31:47.12894+02	{"{\\"msg\\": \\"All resources of type `test::Resource` failed to install handler code dependencies: `ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'`\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"error\\": \\"ExecutorBlueprint.__init__() got an unexpected keyword argument 'sources'\\", \\"res_type\\": \\"test::Resource\\", \\"traceback\\": \\"  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 150, in execute\\\\n    my_executor: executor.Executor = await self.get_executor(\\\\n                                     ^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    ...<3 lines>...\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/deploy/tasks.py\\\\\\", line 88, in get_executor\\\\n    code = await task_manager.code_manager.get_code(\\\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n        environment=task_manager.environment, model_version=version, agent_name=agent_name\\\\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\\\n    )\\\\n    ^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1080, in get_code\\\\n    dummyblueprint: ExecutorBlueprint = _get_dummy_blueprint_for(environment)\\\\n                                        ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/utils.py\\\\\\", line 1065, in _get_dummy_blueprint_for\\\\n    return ExecutorBlueprint(\\\\n        environment_id=environment,\\\\n    ...<3 lines>...\\\\n        sources=[],\\\\n    )\\\\n\\"}, \\"timestamp\\": \\"2026-10-05T08:31:47.128398+02:00\\"}"}	unavailable	\N	nochange	05c96281-a126-4337-9638-1bfbc3b14d5c	2	{"test::Resource[agent1,key=key9],v=2"}
2aaee10e-34bf-46bd-810d-050542ba3181	dryrun	2026-10-05 08:31:47.129842+02	2026-10-05 08:31:47.130574+02	{}	dry	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key5],v=1"}
de653856-11ee-4607-a0c1-74ef4f216a85	dryrun	2026-10-05 08:31:47.132875+02	2026-10-05 08:31:47.133424+02	{}	dry	\N	\N	05c96281-a126-4337-9638-1bfbc3b14d5c	1	{"test::Resource[agent1,key=key6],v=1"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
00e40893-72fb-4684-b14d-61be833dfab4	a5691886-c77f-4c41-ab7c-f4372aa4f8db	fs::File[localhost,path=/tmp/test]	1
00e40893-72fb-4684-b14d-61be833dfab4	a5691886-c77f-4c41-ab7c-f4372aa4f8db	std::AgentConfig[internal,agentname=localhost]	1
00e40893-72fb-4684-b14d-61be833dfab4	0786e121-5116-49dd-8b07-e56289903ce7	std::AgentConfig[internal,agentname=localhost]	1
00e40893-72fb-4684-b14d-61be833dfab4	6550b904-7f62-4e92-a7cd-3cc792d669d3	fs::File[localhost,path=/tmp/test]	1
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	89991d16-918d-479f-930e-a37b2e80e2f0	fs::File[localhost,path=/tmp/test]	1
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	89991d16-918d-479f-930e-a37b2e80e2f0	std::AgentConfig[internal,agentname=localhost]	1
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	7c78a284-6680-4f44-a648-829ef621f06c	std::AgentConfig[internal,agentname=localhost]	1
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	c828955c-342f-4883-a992-e6115f509a72	fs::File[localhost,path=/tmp/test]	1
00e40893-72fb-4684-b14d-61be833dfab4	1b563fa2-6883-402e-b357-3bb7db035414	std::AgentConfig[internal,agentname=localhost]	2
00e40893-72fb-4684-b14d-61be833dfab4	1b563fa2-6883-402e-b357-3bb7db035414	fs::File[localhost,path=/tmp/test]	2
00e40893-72fb-4684-b14d-61be833dfab4	ab7bb0b9-5410-42d6-996f-3bf18dead622	fs::File[localhost,path=/tmp/test_orphan]	3
00e40893-72fb-4684-b14d-61be833dfab4	ab7bb0b9-5410-42d6-996f-3bf18dead622	fs::File[localhost,path=/tmp/test]	3
00e40893-72fb-4684-b14d-61be833dfab4	ab7bb0b9-5410-42d6-996f-3bf18dead622	std::AgentConfig[internal,agentname=localhost]	3
00e40893-72fb-4684-b14d-61be833dfab4	116b1ac8-6b64-4882-80cf-0ac40da57c05	fs::File[localhost,path=/tmp/test_orphan]	3
00e40893-72fb-4684-b14d-61be833dfab4	2b82f1ff-56d1-48e4-bfc3-331fb4ae68e8	fs::File[localhost,path=/tmp/test]	4
00e40893-72fb-4684-b14d-61be833dfab4	2b82f1ff-56d1-48e4-bfc3-331fb4ae68e8	std::AgentConfig[internal,agentname=localhost]	4
00e40893-72fb-4684-b14d-61be833dfab4	97242ebf-c5da-47f4-8cc0-e7786dc79600	std::AgentConfig[internal,agentname=localhost]	5
00e40893-72fb-4684-b14d-61be833dfab4	97242ebf-c5da-47f4-8cc0-e7786dc79600	fs::File[localhost,path=/tmp/test]	5
00e40893-72fb-4684-b14d-61be833dfab4	d8f930ec-8421-4643-9fe0-4b50f0a83092	std::AgentConfig[internal,agentname=localhost]	6
00e40893-72fb-4684-b14d-61be833dfab4	d8f930ec-8421-4643-9fe0-4b50f0a83092	fs::File[localhost,path=/tmp/test]	6
00e40893-72fb-4684-b14d-61be833dfab4	e2062390-ce01-4b44-a497-eeb132e59e86	test::Resource[agent2,key=key2]	7
00e40893-72fb-4684-b14d-61be833dfab4	e2062390-ce01-4b44-a497-eeb132e59e86	test::Resource[agent3,key=key3]	7
00e40893-72fb-4684-b14d-61be833dfab4	e2062390-ce01-4b44-a497-eeb132e59e86	std::AgentConfig[internal,agentname=localhost]	7
00e40893-72fb-4684-b14d-61be833dfab4	e2062390-ce01-4b44-a497-eeb132e59e86	fs::File[localhost,path=/tmp/test]	7
00e40893-72fb-4684-b14d-61be833dfab4	8ead3253-65af-4665-b083-a8f51f9a544f	test::Resource[agent3,key=key3]	7
00e40893-72fb-4684-b14d-61be833dfab4	9e613e23-fbc7-400e-9461-5fae7fb68aa8	test::Resource[agent2,key=key2]	7
00e40893-72fb-4684-b14d-61be833dfab4	b8013e1f-7351-4415-81dd-22ffd88868aa	test::Resource[agent2,key=key2]	8
00e40893-72fb-4684-b14d-61be833dfab4	b8013e1f-7351-4415-81dd-22ffd88868aa	fs::File[localhost,path=/tmp/test]	8
00e40893-72fb-4684-b14d-61be833dfab4	b8013e1f-7351-4415-81dd-22ffd88868aa	std::AgentConfig[internal,agentname=localhost]	8
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Resource[agent1,key=key4]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Resource[agent1,key=key5]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Resource[agent1,key=key3]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Resource[agent1,key=key6]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Resource[agent1,key=key1]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	77f70c9c-3b5d-42be-8642-6d62d9f23d1e	test::Fail[agent1,key=key2]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	62abfd6f-639b-4fcb-ae83-511ab6dd814c	test::Resource[agent1,key=key6]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	e10b81de-2cb5-47ed-9cd1-5394f944f17c	test::Fail[agent1,key=key2]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	81f1392d-599d-4d9f-b5ab-f62e7ea370be	test::Resource[agent1,key=key3]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	37f933b8-6e58-4c6f-b163-8a5f26a29a10	test::Resource[agent1,key=key1]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	b3771416-e5e1-46ce-9092-19c6fd6cf4a7	test::Fail[agent1,key=key2]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key10]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key9]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key1]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key3]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key5]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key11]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Fail[agent1,key=key2]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key7]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2454d4b3-58e3-4ab9-9182-2abd1dfef7b1	test::Resource[agent1,key=key4]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	c017d44f-92b2-4de5-9843-dbb98b13d989	test::Resource[agent1,key=key1]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	d4054ad6-cbd4-451b-a20c-5408783b97fa	test::Resource[agent1,key=key3]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	b7368636-8b8a-48c3-b177-4b224980dba3	test::Resource[agent1,key=key10]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	9439e843-d963-4694-8d82-9b90e8d37351	test::Resource[agent1,key=key7]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	c714a23a-18ef-42bc-97dc-4d11e0b9ee1a	test::Resource[agent1,key=key11]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	752ac25d-b68d-4cf0-8e68-b581aa55ee3c	test::Resource[agent1,key=key9]	2
05c96281-a126-4337-9638-1bfbc3b14d5c	2aaee10e-34bf-46bd-810d-050542ba3181	test::Resource[agent1,key=key5]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	de653856-11ee-4607-a0c1-74ef4f216a85	test::Resource[agent1,key=key6]	1
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key4]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key8]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key3]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key1]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Fail[agent1,key=key2]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key7]	3
05c96281-a126-4337-9638-1bfbc3b14d5c	3ace215d-e03e-446f-b69f-169d3f8f62db	test::Resource[agent1,key=key5]	3
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
5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	1
00e40893-72fb-4684-b14d-61be833dfab4	8
05c96281-a126-4337-9638-1bfbc3b14d5c	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	00e40893-72fb-4684-b14d-61be833dfab4	2026-10-05 08:30:57.130974+02	\N	8bacfdef-13cf-45ea-ba88-37c3339c2947
hugo-Latitude-5421	5e7c5a0a-73d9-4fc5-9d65-e0cb47fdcccb	2026-10-05 08:30:57.237127+02	\N	4d2391cc-45b9-48fe-96c9-8e9f7486092d
hugo-Latitude-5421	05c96281-a126-4337-9638-1bfbc3b14d5c	2026-10-05 08:31:46.85839+02	2026-10-05 08:31:47.225992+02	0418230f-0212-4c90-9ae5-881aa86e644d
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610020,202610050}
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

