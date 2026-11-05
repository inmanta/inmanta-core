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
4904fafb-9125-4019-b382-84902d2f6c06	$__scheduler	f	\N
de13bf55-4719-414f-9232-01370827a37c	$__scheduler	f	\N
6a57d76d-f40a-4834-b564-341324361c0b	$__scheduler	f	\N
4904fafb-9125-4019-b382-84902d2f6c06	localhost	f	\N
de13bf55-4719-414f-9232-01370827a37c	internal	f	\N
de13bf55-4719-414f-9232-01370827a37c	localhost	f	\N
4904fafb-9125-4019-b382-84902d2f6c06	agent2	f	\N
4904fafb-9125-4019-b382-84902d2f6c06	agent3	f	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	agent1	t	t
3c6cf91e-a002-4c91-951b-dd18e0c75b22	$__scheduler	t	t
a7a11756-e1b1-451f-80e3-bab6c69fee55	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
1	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
1	internal	std	de13bf55-4719-414f-9232-01370827a37c
1	localhost	fs	de13bf55-4719-414f-9232-01370827a37c
2	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
2	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
3	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
3	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
4	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
4	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
5	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
5	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
6	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
6	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
7	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
7	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
8	localhost	fs	4904fafb-9125-4019-b382-84902d2f6c06
8	localhost	std	4904fafb-9125-4019-b382-84902d2f6c06
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
346c536a-eee2-49c2-91a0-b3f48ad4d2cf	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:18:57.935789+02	2026-10-13 09:19:14.314248+02	2026-10-13 09:18:57.927126+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	35db7817-0241-43ee-94ed-57c12f8a73f5	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
1c148d62-0059-4c4f-a7e1-c54f45892cb1	de13bf55-4719-414f-9232-01370827a37c	2026-10-13 09:19:14.604105+02	2026-10-13 09:19:29.176178+02	2026-10-13 09:19:14.586343+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	7f42c387-7af8-46c9-89c0-6233f96cb5e3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
9e9932e6-efb8-4f07-8d2d-63940035f6fc	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:29.419798+02	2026-10-13 09:19:30.342677+02	2026-10-13 09:19:29.411123+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	9c252733-9729-4723-a016-ef7daa4e043a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
7117ecec-efdf-41f6-97db-7f793011a05a	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:30.446441+02	2026-10-13 09:19:31.434207+02	2026-10-13 09:19:30.362703+02	{}	{"add_one_resource": "true"}	t	f	t	3	f1007f25-779c-4248-994f-20dc3640220a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
20a48368-7657-41f9-9754-1a4d65a3d37a	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:31.555692+02	2026-10-13 09:19:32.459978+02	2026-10-13 09:19:31.55253+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	c55da821-bebe-4448-a7f3-63ff427525d9	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
cc0e4b9d-f556-4626-9252-6ed0a19c511b	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:32.561043+02	2026-10-13 09:19:33.472264+02	2026-10-13 09:19:32.546552+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	c788648f-b7e1-46ce-adee-b4d59dabc309	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
24da4f64-09b7-4246-ae2d-0f0542219afb	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:33.575712+02	2026-10-13 09:19:47.20958+02	2026-10-13 09:19:33.548694+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	3943557a-da5e-4f50-82a0-75908596fd1d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c4984c5b-4511-412c-b3af-dad9db6daa70	a7a11756-e1b1-451f-80e3-bab6c69fee55	2026-10-13 09:19:48.312449+02	2026-10-13 09:19:48.323119+02	2026-10-13 09:19:48.297889+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	9c725afb-7c53-48d6-a094-b88a8ead1071	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:14.290237+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:47.570439+02	t	\N	2	{}	{}	7	t	\N	\N
1	de13bf55-4719-414f-9232-01370827a37c	2026-10-13 09:19:29.164218+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:30.324294+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:31.425732+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:32.45134+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:33.461687+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:47.199872+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2026-10-13 09:19:47.818076+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:19:47.400941+02	t	\N	3	{}	{}	6	t	\N	\N
2	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2026-10-13 09:19:48.02596+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2026-10-13 09:19:48.172622+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	1	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	1	fs	1.2.0
de13bf55-4719-414f-9232-01370827a37c	1	std	7.0.0
de13bf55-4719-414f-9232-01370827a37c	1	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	2	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	2	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	3	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	3	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	4	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	4	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	5	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	5	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	6	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	6	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	7	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	7	std	8.7.5
4904fafb-9125-4019-b382-84902d2f6c06	8	fs	1.2.0
4904fafb-9125-4019-b382-84902d2f6c06	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	discovery::Discovered[myagent,name=discovered]	{}	2026-10-13 09:19:48.178851+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
4904fafb-9125-4019-b382-84902d2f6c06	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-13 09:19:48.178874+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter) FROM stdin;
19474ba6-45b0-46a0-9515-3a5393cdbfa3	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	2026-10-13 09:19:48.010443+02	6	0	{"14a1def6-7f83-58dc-b4fb-b11a9dcc8444": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "27d18810-9cc9-5986-969e-4b50cd3f2d9b": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "5872d479-1b13-5d59-9ed4-e487b26eaa18": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "5a8b2ffb-58d5-5536-abfa-1c2958ebe7d7": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "5f8bf29e-2f3a-5b09-8f4c-1d3a185d88e6": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "c8b74fb6-6e3d-5dfb-bef2-1379bf31cc0e": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}}	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
a7a11756-e1b1-451f-80e3-bab6c69fee55	dev-4	84e70952-8c9c-456b-addc-485da02545ab			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
4904fafb-9125-4019-b382-84902d2f6c06	dev-1	84e70952-8c9c-456b-addc-485da02545ab			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
de13bf55-4719-414f-9232-01370827a37c	dev-1-twin	84e70952-8c9c-456b-addc-485da02545ab			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
6a57d76d-f40a-4834-b564-341324361c0b	dev-2	84e70952-8c9c-456b-addc-485da02545ab			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
3c6cf91e-a002-4c91-951b-dd18e0c75b22	dev-3	84e70952-8c9c-456b-addc-485da02545ab			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	4904fafb-9125-4019-b382-84902d2f6c06	\N	f
fs	1.2.0	4904fafb-9125-4019-b382-84902d2f6c06	\N	f
std	7.0.0	de13bf55-4719-414f-9232-01370827a37c	\N	f
fs	1.2.0	de13bf55-4719-414f-9232-01370827a37c	\N	f
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
49838a8f-e0c3-44f5-b3b2-aaa297f52bd9	a7a11756-e1b1-451f-80e3-bab6c69fee55	2026-10-13 09:19:48.330927+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/c4984c5b-4511-412c-b3af-dad9db6daa70	f	f	c4984c5b-4511-412c-b3af-dad9db6daa70
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
daa8d3a5-83aa-43d2-a04a-28f0e65858f4	fact1	value1	4904fafb-9125-4019-b382-84902d2f6c06	std::testing::NullResource[localhost,name=test1]	fact	2026-10-13 09:19:32.533012+02	{}	f
347b5f7e-280d-4013-8c48-0628236dec51	fact2	value2	4904fafb-9125-4019-b382-84902d2f6c06	std::testing::NullResource[localhost,name=test2]	fact	2026-10-13 09:19:32.535808+02	{}	t
021278ad-f857-4073-ba7a-f88a4df8c900	fact3	value3	4904fafb-9125-4019-b382-84902d2f6c06	std::testing::NullResource[localhost,name=test3]	fact	2026-10-13 09:19:32.53808+02	{}	t
e71bf3ec-4eb0-4b0e-b24c-e9a4fe12dcdb	parameter1	value1	4904fafb-9125-4019-b382-84902d2f6c06		fact	2026-10-13 09:19:32.540269+02	{}	f
036242a3-1e44-4055-9575-64e1b8324d1d	parameter2	value2	4904fafb-9125-4019-b382-84902d2f6c06		fact	2026-10-13 09:19:32.542432+02	{}	f
7a7a8561-212b-4f0b-b6b8-26094dfd97b8	parameter3	value3	4904fafb-9125-4019-b382-84902d2f6c06		fact	2026-10-13 09:19:32.544589+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
84e70952-8c9c-456b-addc-485da02545ab	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
07b16de1-f27d-4b49-bb9a-77c9f6ec1020	2026-10-13 09:18:57.936175+02	2026-10-13 09:18:57.938624+02		Init		Using extra environment variables during compile \n	0	346c536a-eee2-49c2-91a0-b3f48ad4d2cf
6474b5b1-935e-4764-8065-3c94f733c3ed	2026-10-13 09:18:57.9389+02	2026-10-13 09:18:57.951905+02		Venv check		Creating new venv at /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env-py3.14\n	0	346c536a-eee2-49c2-91a0-b3f48ad4d2cf
87acdc55-c400-4a79-8448-f608df7943a8	2026-10-13 09:18:57.953519+02	2026-10-13 09:18:58.328035+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	346c536a-eee2-49c2-91a0-b3f48ad4d2cf
6bd546b3-6b69-4d9d-a598-dae9580ffcb9	2026-10-13 09:18:58.328726+02	2026-10-13 09:19:13.356094+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpsnd9w2kv:\n                                 Pip command: /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpsnd9w2kv inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.2/2.2 MB 18.2 MB/s  0:00:00\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Downloading strawberry_graphql-0.334.3-py3-none-any.whl (364 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, pydantic-core, mitogen, jsonpath-ng, strawberry-graphql, pydantic, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.10.1 mitogen-0.3.54 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.334.3 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	346c536a-eee2-49c2-91a0-b3f48ad4d2cf
00cf4ed3-e3cd-4829-a9cd-71873f17a674	2026-10-13 09:19:13.356788+02	2026-10-13 09:19:14.313138+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpx9p9235a --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.019 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.027 seconds\ncompiler       DEBUG   The entire export command took 0.078 seconds\n	0	346c536a-eee2-49c2-91a0-b3f48ad4d2cf
b3f50f10-7626-4e75-a486-5af0bdad91fa	2026-10-13 09:19:14.605581+02	2026-10-13 09:19:14.614238+02		Init		Using extra environment variables during compile \n	0	1c148d62-0059-4c4f-a7e1-c54f45892cb1
70c69e3c-9533-44df-8691-90821de2b0dc	2026-10-13 09:19:14.615422+02	2026-10-13 09:19:14.651758+02		Venv check		Creating new venv at /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env-py3.14\n	0	1c148d62-0059-4c4f-a7e1-c54f45892cb1
7ce8d9de-2611-4cdc-90fe-b1d5756096fc	2026-10-13 09:19:14.656102+02	2026-10-13 09:19:15.0047+02	/tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	1c148d62-0059-4c4f-a7e1-c54f45892cb1
487acbd6-f24a-4d7a-9509-9c7feac0629d	2026-10-13 09:19:29.420135+02	2026-10-13 09:19:29.422294+02		Init		Using extra environment variables during compile \n	0	9e9932e6-efb8-4f07-8d2d-63940035f6fc
a76bf588-6a45-4f66-965f-3da536e369f6	2026-10-13 09:19:29.422546+02	2026-10-13 09:19:29.423037+02		Venv check		Found existing venv\n	0	9e9932e6-efb8-4f07-8d2d-63940035f6fc
6b07b70e-728a-4500-8249-5ce618057c79	2026-10-13 09:19:15.005464+02	2026-10-13 09:19:28.231028+02	/tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpk3o2z84r:\n                                 Pip command: /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpk3o2z84r inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.334.3-py3-none-any.whl (364 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, pydantic-core, mitogen, jsonpath-ng, strawberry-graphql, pydantic, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.10.1 mitogen-0.3.54 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.334.3 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	1c148d62-0059-4c4f-a7e1-c54f45892cb1
00600036-48f7-4a04-bbc4-9ce7b2fa5fe8	2026-10-13 09:19:28.231815+02	2026-10-13 09:19:29.175742+02	/tmp/tmpq16z1rwn/server/de13bf55-4719-414f-9232-01370827a37c/compiler/.env/bin/python -m inmanta.app -vvv export -X -e de13bf55-4719-414f-9232-01370827a37c --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpg84767a2 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	1c148d62-0059-4c4f-a7e1-c54f45892cb1
1ce1a06c-e981-46d4-8721-f4d9e91df498	2026-10-13 09:19:31.556173+02	2026-10-13 09:19:31.559122+02		Init		Using extra environment variables during compile \n	0	20a48368-7657-41f9-9754-1a4d65a3d37a
b50bac1e-7522-4d30-b667-8c40ec4e8ad7	2026-10-13 09:19:31.559385+02	2026-10-13 09:19:31.559785+02		Venv check		Found existing venv\n	0	20a48368-7657-41f9-9754-1a4d65a3d37a
aa344462-2a94-423f-82f0-de08ff2006e5	2026-10-13 09:19:29.423208+02	2026-10-13 09:19:30.342013+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp5_of07bt --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.021 seconds\ncompiler       DEBUG   The entire export command took 0.060 seconds\n	0	9e9932e6-efb8-4f07-8d2d-63940035f6fc
8a6b81e0-73f2-4064-93dc-93a42e282037	2026-10-13 09:19:30.448433+02	2026-10-13 09:19:30.457803+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	7117ecec-efdf-41f6-97db-7f793011a05a
19babc3a-cb08-4605-ae93-eff1ab5d12ab	2026-10-13 09:19:30.459033+02	2026-10-13 09:19:30.461343+02		Venv check		Found existing venv\n	0	7117ecec-efdf-41f6-97db-7f793011a05a
d4d12be3-77e1-48cd-91b3-a5693d962f0b	2026-10-13 09:19:30.462437+02	2026-10-13 09:19:31.433612+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmphugm5pvz --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	7117ecec-efdf-41f6-97db-7f793011a05a
73bbedab-5cb1-4efb-aa93-49c97e3b447f	2026-10-13 09:19:31.559975+02	2026-10-13 09:19:32.459447+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp1uecwwgj --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.050 seconds\n	0	20a48368-7657-41f9-9754-1a4d65a3d37a
4ee7733e-135f-4ba8-ab82-7a294b2fad6b	2026-10-13 09:19:32.561394+02	2026-10-13 09:19:32.563479+02		Init		Using extra environment variables during compile \n	0	cc0e4b9d-f556-4626-9252-6ed0a19c511b
104b72e2-5823-4b92-bc8a-ed2d90fc4dce	2026-10-13 09:19:32.563682+02	2026-10-13 09:19:32.564075+02		Venv check		Found existing venv\n	0	cc0e4b9d-f556-4626-9252-6ed0a19c511b
7617f9fc-1f47-49c8-8dd9-1e700eb0b6a2	2026-10-13 09:19:32.564238+02	2026-10-13 09:19:33.471895+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpl6k_i1ji --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	cc0e4b9d-f556-4626-9252-6ed0a19c511b
eb05bafe-7bee-4208-958b-b36905a03895	2026-10-13 09:19:33.577381+02	2026-10-13 09:19:33.585178+02		Init		Using extra environment variables during compile \n	0	24da4f64-09b7-4246-ae2d-0f0542219afb
69d06d1d-ddb8-433d-be33-2b4a44c0c1c5	2026-10-13 09:19:33.586108+02	2026-10-13 09:19:33.588192+02		Venv check		Found existing venv\n	0	24da4f64-09b7-4246-ae2d-0f0542219afb
4f04d58c-7559-463f-a60a-3017b5073f85	2026-10-13 09:19:33.592261+02	2026-10-13 09:19:33.937019+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	24da4f64-09b7-4246-ae2d-0f0542219afb
a4dabde1-09e7-4223-b2b6-00741ebbe845	2026-10-13 09:19:33.9377+02	2026-10-13 09:19:46.248424+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpybb7jf7a:\n                                 Pip command: /tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpybb7jf7a inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.0.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in ./.env/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.334.3)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.0.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	24da4f64-09b7-4246-ae2d-0f0542219afb
4c2bf926-2105-45af-8262-7df1fd306f50	2026-10-13 09:19:46.24919+02	2026-10-13 09:19:47.209202+02	/tmp/tmpq16z1rwn/server/4904fafb-9125-4019-b382-84902d2f6c06/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4904fafb-9125-4019-b382-84902d2f6c06 --server_address localhost --server_port 36661 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpj4xfe5y9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:36661/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:36661/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	24da4f64-09b7-4246-ae2d-0f0542219afb
5ef43d1b-6416-4e91-ba56-bdc362025d3e	2026-10-13 09:19:48.314423+02	2026-10-13 09:19:48.321479+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpq16z1rwn/server/a7a11756-e1b1-451f-80e3-bab6c69fee55/compiler and no repository set.\n	1	c4984c5b-4511-412c-b3af-dad9db6daa70
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	dd2d9810-4f83-4bba-a21f-a2e02d87538c
de13bf55-4719-414f-9232-01370827a37c	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	e91f3723-2133-4443-8999-d5c0565a93c8
de13bf55-4719-414f-9232-01370827a37c	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e91f3723-2133-4443-8999-d5c0565a93c8
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6ef3105e-21fa-456f-9054-b0884a5777db
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a9525b80-f1f4-4466-a166-95834be48302
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	a9525b80-f1f4-4466-a166-95834be48302
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	048adcce-2d57-4723-ad8d-1da42c0cd3d6
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	2f66334c-9525-4ea7-ae06-aec848dd5d33
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0386f22f-ad10-457a-9cb4-2a0eb15a28b6
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	60da5e78-8d63-4d49-8ee9-fafc0c2427c2
4904fafb-9125-4019-b382-84902d2f6c06	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	e0d68a04-d74b-49b4-b00c-bbb076f64cd1
4904fafb-9125-4019-b382-84902d2f6c06	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	f3ab4e9f-7fbd-4a4e-b6ff-ca3f90f8835e
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6cccd6ce-d2a2-482a-b001-0c0b048a7c95
4904fafb-9125-4019-b382-84902d2f6c06	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	08d8beee-e2b6-4477-bb55-0fa211d97c45
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	d6a579be-f70e-4c50-86a9-36077e7926a4
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	d6a579be-f70e-4c50-86a9-36077e7926a4
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
88c127d9-93b7-4881-8c5d-65e270b1d3b7	3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-13 09:19:48.09749+02
2d41791e-40e2-494f-b33c-d4ad1511a0dc	3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-13 09:19:48.101742+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key1]	2026-10-13 09:19:47.930788+02	2026-10-13 09:19:47.873113+02	2026-10-13 09:19:47.930788+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:47.854347+02	t	\N	\N
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test]	2026-10-13 09:19:14.464222+02	\N	2026-10-13 09:19:14.464222+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:14.429628+02	f	\N	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key10]	2026-10-13 09:19:48.09749+02	\N	2026-10-13 09:19:48.09749+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:48.031971+02	f	88c127d9-93b7-4881-8c5d-65e270b1d3b7	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Fail[agent1,key=key2]	2026-10-13 09:19:47.94203+02	\N	2026-10-13 09:19:47.94203+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:47.854347+02	f	\N	\N
de13bf55-4719-414f-9232-01370827a37c	std::AgentConfig[internal,agentname=localhost]	2026-10-13 09:19:29.285662+02	\N	2026-10-13 09:19:29.285662+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:29.254792+02	f	\N	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key3]	2026-10-13 09:19:47.948149+02	\N	2026-10-13 09:19:47.948149+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-13 09:19:47.854347+02	f	\N	\N
de13bf55-4719-414f-9232-01370827a37c	fs::File[localhost,path=/tmp/test]	2026-10-13 09:19:29.306674+02	\N	2026-10-13 09:19:29.306674+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:29.254792+02	f	\N	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key11]	2026-10-13 09:19:48.101742+02	\N	2026-10-13 09:19:48.101742+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:48.031971+02	f	2d41791e-40e2-494f-b33c-d4ad1511a0dc	\N
4904fafb-9125-4019-b382-84902d2f6c06	fs::File[localhost,path=/tmp/test_orphan]	2026-10-13 09:19:31.548089+02	\N	2026-10-13 09:19:31.548089+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:31.541003+02	f	\N	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key9]	2026-10-13 09:19:48.10549+02	2026-10-13 09:19:48.102636+02	2026-10-13 09:19:48.10549+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:48.031971+02	t	\N	\N
4904fafb-9125-4019-b382-84902d2f6c06	test::Resource[agent2,key=key2]	2026-10-13 09:19:47.435602+02	\N	2026-10-13 09:19:47.435602+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:47.426519+02	f	\N	\N
4904fafb-9125-4019-b382-84902d2f6c06	test::Resource[agent3,key=key3]	2026-10-13 09:19:47.43409+02	\N	2026-10-13 09:19:47.43409+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-13 09:19:47.426519+02	f	\N	7
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-13 09:19:47.854347+02	\N	\N	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-13 09:19:47.854347+02	\N	\N	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key6]	2026-10-13 09:19:47.954446+02	2026-10-13 09:19:47.949931+02	2026-10-13 09:19:47.954446+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:47.854347+02	t	\N	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	test::Resource[agent1,key=key7]	2026-10-13 09:19:48.093164+02	2026-10-13 09:19:48.080174+02	2026-10-13 09:19:48.093164+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-13 09:19:48.031971+02	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	dd2d9810-4f83-4bba-a21f-a2e02d87538c	\N
de13bf55-4719-414f-9232-01370827a37c	e91f3723-2133-4443-8999-d5c0565a93c8	\N
4904fafb-9125-4019-b382-84902d2f6c06	6ef3105e-21fa-456f-9054-b0884a5777db	\N
4904fafb-9125-4019-b382-84902d2f6c06	a9525b80-f1f4-4466-a166-95834be48302	\N
4904fafb-9125-4019-b382-84902d2f6c06	048adcce-2d57-4723-ad8d-1da42c0cd3d6	\N
4904fafb-9125-4019-b382-84902d2f6c06	2f66334c-9525-4ea7-ae06-aec848dd5d33	\N
4904fafb-9125-4019-b382-84902d2f6c06	0386f22f-ad10-457a-9cb4-2a0eb15a28b6	\N
4904fafb-9125-4019-b382-84902d2f6c06	60da5e78-8d63-4d49-8ee9-fafc0c2427c2	\N
4904fafb-9125-4019-b382-84902d2f6c06	e0d68a04-d74b-49b4-b00c-bbb076f64cd1	set-b
4904fafb-9125-4019-b382-84902d2f6c06	f3ab4e9f-7fbd-4a4e-b6ff-ca3f90f8835e	set-a
4904fafb-9125-4019-b382-84902d2f6c06	6cccd6ce-d2a2-482a-b001-0c0b048a7c95	\N
4904fafb-9125-4019-b382-84902d2f6c06	08d8beee-e2b6-4477-bb55-0fa211d97c45	set-a
3c6cf91e-a002-4c91-951b-dd18e0c75b22	d1f76d55-06ae-4064-81f3-ef0a554eadc5	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	723d6694-8879-4b7f-be7d-13cd1cea1493	\N
3c6cf91e-a002-4c91-951b-dd18e0c75b22	d6a579be-f70e-4c50-86a9-36077e7926a4	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	1	dd2d9810-4f83-4bba-a21f-a2e02d87538c
de13bf55-4719-414f-9232-01370827a37c	1	e91f3723-2133-4443-8999-d5c0565a93c8
4904fafb-9125-4019-b382-84902d2f6c06	2	6ef3105e-21fa-456f-9054-b0884a5777db
4904fafb-9125-4019-b382-84902d2f6c06	3	a9525b80-f1f4-4466-a166-95834be48302
4904fafb-9125-4019-b382-84902d2f6c06	4	048adcce-2d57-4723-ad8d-1da42c0cd3d6
4904fafb-9125-4019-b382-84902d2f6c06	5	2f66334c-9525-4ea7-ae06-aec848dd5d33
4904fafb-9125-4019-b382-84902d2f6c06	6	0386f22f-ad10-457a-9cb4-2a0eb15a28b6
4904fafb-9125-4019-b382-84902d2f6c06	7	60da5e78-8d63-4d49-8ee9-fafc0c2427c2
4904fafb-9125-4019-b382-84902d2f6c06	7	e0d68a04-d74b-49b4-b00c-bbb076f64cd1
4904fafb-9125-4019-b382-84902d2f6c06	7	f3ab4e9f-7fbd-4a4e-b6ff-ca3f90f8835e
4904fafb-9125-4019-b382-84902d2f6c06	8	6cccd6ce-d2a2-482a-b001-0c0b048a7c95
4904fafb-9125-4019-b382-84902d2f6c06	8	08d8beee-e2b6-4477-bb55-0fa211d97c45
3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	d1f76d55-06ae-4064-81f3-ef0a554eadc5
3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	723d6694-8879-4b7f-be7d-13cd1cea1493
3c6cf91e-a002-4c91-951b-dd18e0c75b22	3	d6a579be-f70e-4c50-86a9-36077e7926a4
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
b0e545bf-69f1-4ef8-960e-a7164223f609	store	2026-10-13 09:19:14.290179+02	2026-10-13 09:19:14.30198+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-13T09:19:14.301996+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	1	{"fs::File[localhost,path=/tmp/test],v=1"}
c7ff82c5-3059-42d8-af79-073e98442304	deploy	2026-10-13 09:19:14.456978+02	2026-10-13 09:19:14.464222+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:14.463356+02:00\\"}"}	unavailable	\N	nochange	4904fafb-9125-4019-b382-84902d2f6c06	1	{"fs::File[localhost,path=/tmp/test],v=1"}
2acab9a0-5031-48bd-af9b-9095e3f73e48	store	2026-10-13 09:19:29.164161+02	2026-10-13 09:19:29.169691+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-13T09:19:29.169701+02:00\\"}"}	\N	\N	\N	de13bf55-4719-414f-9232-01370827a37c	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
d83108a5-52d7-45f6-ad35-23bfa5aed264	deploy	2026-10-13 09:19:29.276702+02	2026-10-13 09:19:29.285662+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:29.283970+02:00\\"}"}	unavailable	\N	nochange	de13bf55-4719-414f-9232-01370827a37c	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
2e9759aa-3749-443b-a794-e09fc90da033	deploy	2026-10-13 09:19:29.301645+02	2026-10-13 09:19:29.306674+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:29.305321+02:00\\"}"}	unavailable	\N	nochange	de13bf55-4719-414f-9232-01370827a37c	1	{"fs::File[localhost,path=/tmp/test],v=1"}
9058cbf4-607d-43c1-a8d3-92d090d72d34	store	2026-10-13 09:19:30.324244+02	2026-10-13 09:19:30.330446+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-13T09:19:30.330460+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	2	{"fs::File[localhost,path=/tmp/test],v=2"}
190f2337-33be-4a18-a715-b399b8a2a9a3	store	2026-10-13 09:19:31.425685+02	2026-10-13 09:19:31.427735+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-13T09:19:31.427742+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
11f47998-6ac5-4d7f-b7b5-d7fc1f9cff16	deploy	2026-10-13 09:19:31.545541+02	2026-10-13 09:19:31.548089+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-13T09:19:31.547347+02:00\\"}"}	unavailable	\N	nochange	4904fafb-9125-4019-b382-84902d2f6c06	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
d9e59b1a-0742-4fb1-8664-b2340ce4d63e	store	2026-10-13 09:19:32.45129+02	2026-10-13 09:19:32.453284+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-13T09:19:32.453293+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	4	{"fs::File[localhost,path=/tmp/test],v=4"}
6ad385ef-7748-467e-be53-792a4a42b190	store	2026-10-13 09:19:33.461595+02	2026-10-13 09:19:33.464576+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-13T09:19:33.464591+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	5	{"fs::File[localhost,path=/tmp/test],v=5"}
7b344425-53ae-469a-bf50-4f03d087dc75	store	2026-10-13 09:19:47.199818+02	2026-10-13 09:19:47.201696+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-13T09:19:47.201705+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	6	{"fs::File[localhost,path=/tmp/test],v=6"}
e7aff3e5-2a30-4307-8891-cb935ceef673	store	2026-10-13 09:19:47.400845+02	2026-10-13 09:19:47.404928+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-13T09:19:47.404936+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	7	{"test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7"}
25e6fb69-f207-4e46-aaea-725ed81d4b99	deploy	2026-10-13 09:19:47.431902+02	2026-10-13 09:19:47.43409+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.433505+02:00\\"}"}	unavailable	\N	nochange	4904fafb-9125-4019-b382-84902d2f6c06	7	{"test::Resource[agent3,key=key3],v=7"}
97e20feb-00f2-41f8-b99c-7b033652a116	deploy	2026-10-13 09:19:47.434149+02	2026-10-13 09:19:47.435602+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.435121+02:00\\"}"}	unavailable	\N	nochange	4904fafb-9125-4019-b382-84902d2f6c06	7	{"test::Resource[agent2,key=key2],v=7"}
9e8e8813-4a48-46d7-969f-e6bc98df156c	store	2026-10-13 09:19:47.569779+02	2026-10-13 09:19:47.591465+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-13T09:19:47.591501+02:00\\"}"}	\N	\N	\N	4904fafb-9125-4019-b382-84902d2f6c06	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
177d967a-3737-46a8-8614-24514ac0f20d	store	2026-10-13 09:19:47.817589+02	2026-10-13 09:19:47.82761+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-13T09:19:47.827644+02:00\\"}"}	\N	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key3],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key1],v=1"}
15d0ee40-0292-4d10-9395-25a40729b572	deploy	2026-10-13 09:19:47.873266+02	2026-10-13 09:19:47.930788+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 79ce026f-756a-47cf-a408-679f76f21614).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"79ce026f-756a-47cf-a408-679f76f21614\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.904155+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 79ce026f-756a-47cf-a408-679f76f21614) - duration: 0.0262 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.026178359985351562, \\"deploy_id\\": \\"79ce026f-756a-47cf-a408-679f76f21614\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.930626+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key1],v=1"}
ed170b94-0c50-42a8-9842-c03d759e216c	deploy	2026-10-13 09:19:47.937301+02	2026-10-13 09:19:47.94203+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 04085271-c61c-4f96-819d-f583a8cc91c2).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"04085271-c61c-4f96-819d-f583a8cc91c2\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.940556+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.941227+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 04085271-c61c-4f96-819d-f583a8cc91c2) - duration: 0.0013 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0012598037719726562, \\"deploy_id\\": \\"04085271-c61c-4f96-819d-f583a8cc91c2\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.941938+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Fail[agent1,key=key2],v=1"}
77917897-9ef9-46dc-84dc-4b63edaec22a	deploy	2026-10-13 09:19:47.9453+02	2026-10-13 09:19:47.948149+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 99631503-99ad-4283-8748-fa17521ec3d8).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"99631503-99ad-4283-8748-fa17521ec3d8\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.947478+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.947777+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 99631503-99ad-4283-8748-fa17521ec3d8) - duration: 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0004246234893798828, \\"deploy_id\\": \\"99631503-99ad-4283-8748-fa17521ec3d8\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.948060+02:00\\"}"}	skipped	\N	nochange	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key3],v=1"}
ffeadf91-98d9-4819-91ff-41ecdc65cccd	deploy	2026-10-13 09:19:47.949969+02	2026-10-13 09:19:47.954446+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: c052b672-7b7a-4483-b4ea-8baf751e9114).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"c052b672-7b7a-4483-b4ea-8baf751e9114\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.950794+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: c052b672-7b7a-4483-b4ea-8baf751e9114) - duration: 0.0036 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0035750865936279297, \\"deploy_id\\": \\"c052b672-7b7a-4483-b4ea-8baf751e9114\\"}, \\"timestamp\\": \\"2026-10-13T09:19:47.954413+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key6],v=1"}
ca30b734-cc26-4047-b094-5fe4b96a2896	dryrun	2026-10-13 09:19:48.017477+02	2026-10-13 09:19:48.017948+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.017542+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003294944763183594, \\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.017929+02:00\\"}"}	dry	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Fail[agent1,key=key2],v=1"}
5b9d4d7e-de40-4699-a3a2-2bbd8ceec406	dryrun	2026-10-13 09:19:48.022235+02	2026-10-13 09:19:48.022598+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.022281+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002579689025878906, \\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.022583+02:00\\"}"}	dry	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key1],v=1"}
e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	store	2026-10-13 09:19:48.025903+02	2026-10-13 09:19:48.028584+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-13T09:19:48.028589+02:00\\"}"}	\N	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	{"test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key10],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key3],v=2"}
d78db6e7-b3f1-4770-8ac1-fc04981c51c8	dryrun	2026-10-13 09:19:48.026137+02	2026-10-13 09:19:48.026576+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.026185+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00033974647521972656, \\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.026562+02:00\\"}"}	dry	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key3],v=1"}
ac27a809-f76f-4054-81f6-692a59f45dac	dryrun	2026-10-13 09:19:48.028441+02	2026-10-13 09:19:48.028849+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.028484+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003142356872558594, \\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.028836+02:00\\"}"}	dry	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key5],v=1"}
69bb34ff-8266-406b-af46-41db14949625	dryrun	2026-10-13 09:19:48.031397+02	2026-10-13 09:19:48.031675+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.031435+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 19474ba6-45b0-46a0-9515-3a5393cdbfa3 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00018930435180664062, \\"dry_run_id\\": \\"19474ba6-45b0-46a0-9515-3a5393cdbfa3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.031661+02:00\\"}"}	dry	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	1	{"test::Resource[agent1,key=key6],v=1"}
ef2217f6-d25c-41ad-a91d-8052ab6a43e7	store	2026-10-13 09:19:48.172577+02	2026-10-13 09:19:48.177054+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-13T09:19:48.177062+02:00\\"}"}	\N	\N	\N	3c6cf91e-a002-4c91-951b-dd18e0c75b22	3	{"test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key3],v=3"}
be235977-2ec7-458a-8e8e-85976ce3d366	deploy	2026-10-13 09:19:48.080328+02	2026-10-13 09:19:48.093164+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f3b3b856-393b-4d9c-983d-af25cfa9f369).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"f3b3b856-393b-4d9c-983d-af25cfa9f369\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.088324+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: f3b3b856-393b-4d9c-983d-af25cfa9f369) - duration: 0.0047 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.004712581634521484, \\"deploy_id\\": \\"f3b3b856-393b-4d9c-983d-af25cfa9f369\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.093129+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	{"test::Resource[agent1,key=key7],v=2"}
d1f6a68f-ef78-457c-9f7a-053c51f0b751	deploy	2026-10-13 09:19:48.094336+02	2026-10-13 09:19:48.09749+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 8bcbe288-d8eb-4278-999f-0ca559ecd7a3).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"8bcbe288-d8eb-4278-999f-0ca559ecd7a3\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.094956+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.095150+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 8bcbe288-d8eb-4278-999f-0ca559ecd7a3) - duration: 0.0025 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.002462625503540039, \\"deploy_id\\": \\"8bcbe288-d8eb-4278-999f-0ca559ecd7a3\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.097459+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	{"test::Resource[agent1,key=key10],v=2"}
298ef5bc-d4b1-4905-b661-e2f153389811	deploy	2026-10-13 09:19:48.098804+02	2026-10-13 09:19:48.101742+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: af5b3ca9-11d4-41f7-94d7-fd87cdb0e188).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"af5b3ca9-11d4-41f7-94d7-fd87cdb0e188\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.099361+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.099529+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: af5b3ca9-11d4-41f7-94d7-fd87cdb0e188) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.002312898635864258, \\"deploy_id\\": \\"af5b3ca9-11d4-41f7-94d7-fd87cdb0e188\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.101714+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	{"test::Resource[agent1,key=key11],v=2"}
8b49cd97-6b9a-447d-b328-82d616dcf274	deploy	2026-10-13 09:19:48.102661+02	2026-10-13 09:19:48.10549+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 96c6e989-940d-48e2-91c3-9fa878114ab4).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"96c6e989-940d-48e2-91c3-9fa878114ab4\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.103201+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 96c6e989-940d-48e2-91c3-9fa878114ab4) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.002221345901489258, \\"deploy_id\\": \\"96c6e989-940d-48e2-91c3-9fa878114ab4\\"}, \\"timestamp\\": \\"2026-10-13T09:19:48.105461+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2	{"test::Resource[agent1,key=key9],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
4904fafb-9125-4019-b382-84902d2f6c06	b0e545bf-69f1-4ef8-960e-a7164223f609	fs::File[localhost,path=/tmp/test]	1
4904fafb-9125-4019-b382-84902d2f6c06	c7ff82c5-3059-42d8-af79-073e98442304	fs::File[localhost,path=/tmp/test]	1
de13bf55-4719-414f-9232-01370827a37c	2acab9a0-5031-48bd-af9b-9095e3f73e48	fs::File[localhost,path=/tmp/test]	1
de13bf55-4719-414f-9232-01370827a37c	2acab9a0-5031-48bd-af9b-9095e3f73e48	std::AgentConfig[internal,agentname=localhost]	1
de13bf55-4719-414f-9232-01370827a37c	d83108a5-52d7-45f6-ad35-23bfa5aed264	std::AgentConfig[internal,agentname=localhost]	1
de13bf55-4719-414f-9232-01370827a37c	2e9759aa-3749-443b-a794-e09fc90da033	fs::File[localhost,path=/tmp/test]	1
4904fafb-9125-4019-b382-84902d2f6c06	9058cbf4-607d-43c1-a8d3-92d090d72d34	fs::File[localhost,path=/tmp/test]	2
4904fafb-9125-4019-b382-84902d2f6c06	190f2337-33be-4a18-a715-b399b8a2a9a3	fs::File[localhost,path=/tmp/test_orphan]	3
4904fafb-9125-4019-b382-84902d2f6c06	190f2337-33be-4a18-a715-b399b8a2a9a3	fs::File[localhost,path=/tmp/test]	3
4904fafb-9125-4019-b382-84902d2f6c06	11f47998-6ac5-4d7f-b7b5-d7fc1f9cff16	fs::File[localhost,path=/tmp/test_orphan]	3
4904fafb-9125-4019-b382-84902d2f6c06	d9e59b1a-0742-4fb1-8664-b2340ce4d63e	fs::File[localhost,path=/tmp/test]	4
4904fafb-9125-4019-b382-84902d2f6c06	6ad385ef-7748-467e-be53-792a4a42b190	fs::File[localhost,path=/tmp/test]	5
4904fafb-9125-4019-b382-84902d2f6c06	7b344425-53ae-469a-bf50-4f03d087dc75	fs::File[localhost,path=/tmp/test]	6
4904fafb-9125-4019-b382-84902d2f6c06	e7aff3e5-2a30-4307-8891-cb935ceef673	test::Resource[agent3,key=key3]	7
4904fafb-9125-4019-b382-84902d2f6c06	e7aff3e5-2a30-4307-8891-cb935ceef673	fs::File[localhost,path=/tmp/test]	7
4904fafb-9125-4019-b382-84902d2f6c06	e7aff3e5-2a30-4307-8891-cb935ceef673	test::Resource[agent2,key=key2]	7
4904fafb-9125-4019-b382-84902d2f6c06	25e6fb69-f207-4e46-aaea-725ed81d4b99	test::Resource[agent3,key=key3]	7
4904fafb-9125-4019-b382-84902d2f6c06	97e20feb-00f2-41f8-b99c-7b033652a116	test::Resource[agent2,key=key2]	7
4904fafb-9125-4019-b382-84902d2f6c06	9e8e8813-4a48-46d7-969f-e6bc98df156c	test::Resource[agent2,key=key2]	8
4904fafb-9125-4019-b382-84902d2f6c06	9e8e8813-4a48-46d7-969f-e6bc98df156c	fs::File[localhost,path=/tmp/test]	8
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Resource[agent1,key=key4]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Resource[agent1,key=key6]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Resource[agent1,key=key5]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Resource[agent1,key=key3]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Fail[agent1,key=key2]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	177d967a-3737-46a8-8614-24514ac0f20d	test::Resource[agent1,key=key1]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	15d0ee40-0292-4d10-9395-25a40729b572	test::Resource[agent1,key=key1]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ed170b94-0c50-42a8-9842-c03d759e216c	test::Fail[agent1,key=key2]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	77917897-9ef9-46dc-84dc-4b63edaec22a	test::Resource[agent1,key=key3]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ffeadf91-98d9-4819-91ff-41ecdc65cccd	test::Resource[agent1,key=key6]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ca30b734-cc26-4047-b094-5fe4b96a2896	test::Fail[agent1,key=key2]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	5b9d4d7e-de40-4699-a3a2-2bbd8ceec406	test::Resource[agent1,key=key1]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	d78db6e7-b3f1-4770-8ac1-fc04981c51c8	test::Resource[agent1,key=key3]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key7]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key10]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Fail[agent1,key=key2]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key4]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key1]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key5]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key11]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key9]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	e6cf6f20-1ab2-4bd5-a425-bf5203d053e6	test::Resource[agent1,key=key3]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ac27a809-f76f-4054-81f6-692a59f45dac	test::Resource[agent1,key=key5]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	69bb34ff-8266-406b-af46-41db14949625	test::Resource[agent1,key=key6]	1
3c6cf91e-a002-4c91-951b-dd18e0c75b22	be235977-2ec7-458a-8e8e-85976ce3d366	test::Resource[agent1,key=key7]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	d1f6a68f-ef78-457c-9f7a-053c51f0b751	test::Resource[agent1,key=key10]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	298ef5bc-d4b1-4905-b661-e2f153389811	test::Resource[agent1,key=key11]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	8b49cd97-6b9a-447d-b328-82d616dcf274	test::Resource[agent1,key=key9]	2
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Fail[agent1,key=key2]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key4]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key8]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key7]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key5]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key1]	3
3c6cf91e-a002-4c91-951b-dd18e0c75b22	ef2217f6-d25c-41ad-a91d-8052ab6a43e7	test::Resource[agent1,key=key3]	3
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
de13bf55-4719-414f-9232-01370827a37c	1
4904fafb-9125-4019-b382-84902d2f6c06	8
3c6cf91e-a002-4c91-951b-dd18e0c75b22	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	4904fafb-9125-4019-b382-84902d2f6c06	2026-10-13 09:18:57.670344+02	\N	ff8a21e1-ecbb-4132-b648-b972002aa4c6
hugo-Latitude-5421	de13bf55-4719-414f-9232-01370827a37c	2026-10-13 09:18:57.803344+02	\N	9bfe0da8-eac4-477b-acec-fe0e657e5e5e
hugo-Latitude-5421	3c6cf91e-a002-4c91-951b-dd18e0c75b22	2026-10-13 09:19:47.669805+02	2026-10-13 09:19:48.168565+02	853b2f14-a4b9-48da-a134-6e6f875f962b
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051}
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

