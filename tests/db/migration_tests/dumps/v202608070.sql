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
6e6c04f7-6582-452b-9f49-84cf2f406b27	$__scheduler	f	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	$__scheduler	f	\N
3d7a6f89-d034-4234-8cf7-4217cb1cbf11	$__scheduler	f	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	internal	f	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	localhost	f	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	internal	f	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	localhost	f	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	agent2	f	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	agent3	f	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	agent1	t	t
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	$__scheduler	t	t
73cb3ae7-f0e9-4ed6-b1de-8c2b0ef90a85	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
1	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
1	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
1	internal	std	2c27f7f5-7be2-49ab-9e15-4f4f533be175
1	localhost	fs	2c27f7f5-7be2-49ab-9e15-4f4f533be175
2	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
2	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
2	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
3	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
3	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
3	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
4	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
4	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
4	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
5	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
5	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
5	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
6	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
6	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
6	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
7	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
7	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
7	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
8	localhost	fs	6e6c04f7-6582-452b-9f49-84cf2f406b27
8	internal	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
8	localhost	std	6e6c04f7-6582-452b-9f49-84cf2f406b27
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
f7ac53d5-703f-4be4-b429-730ca79d4895	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:14:47.11736+02	2026-09-11 11:15:02.127873+02	2026-09-11 11:14:47.106924+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	ea3a4a55-4a11-4a8f-95e2-f5128170a82c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bad8c95a-a948-4a96-927b-4319aa841848	2c27f7f5-7be2-49ab-9e15-4f4f533be175	2026-09-11 11:15:02.395194+02	2026-09-11 11:15:15.56979+02	2026-09-11 11:15:02.377383+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	911a08c2-ea1b-4cf2-a8c9-6ce17ba7d2c3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
da2dcb7a-78ed-48c3-89c8-07866bb7d145	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:15.764633+02	2026-09-11 11:15:16.685977+02	2026-09-11 11:15:15.758574+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	45c97a99-510f-41cc-8e8f-0a9ce4437c96	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c6164f82-a9f4-4e89-afad-7d9d0d32ebfa	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:16.788288+02	2026-09-11 11:15:17.676952+02	2026-09-11 11:15:16.710332+02	{}	{"add_one_resource": "true"}	t	f	t	3	144e7d66-9944-4c0c-89fd-97f87cebbbd3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
928dad06-ef8b-438d-96e0-f89220e8c283	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:17.925577+02	2026-09-11 11:15:18.826466+02	2026-09-11 11:15:17.91009+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	46f71f33-8c23-4dff-b24b-0c2dd8cf2df0	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
b986bebd-52ca-488d-864c-efdfaee36706	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:18.927662+02	2026-09-11 11:15:19.825799+02	2026-09-11 11:15:18.89527+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	bdfbfc30-5123-4395-a43a-ee3ba7e542eb	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a344e723-96c2-42e3-8e54-cab93a31c5af	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:19.929974+02	2026-09-11 11:15:32.389775+02	2026-09-11 11:15:19.851845+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	abfbb1d8-0801-4807-b179-ed4c04cc2818	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bd6f5e95-781a-4f90-a688-8bac094f3832	73cb3ae7-f0e9-4ed6-b1de-8c2b0ef90a85	2026-09-11 11:15:33.236397+02	2026-09-11 11:15:33.246649+02	2026-09-11 11:15:33.222247+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	f1991be7-658c-4f43-96f2-2bde476d9ee7	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:02.110913+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:32.684078+02	t	\N	3	{}	{}	7	t	\N	\N
1	2c27f7f5-7be2-49ab-9e15-4f4f533be175	2026-09-11 11:15:15.557302+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:16.677085+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:17.667458+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:18.814544+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:19.816305+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:32.38069+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2026-09-11 11:15:32.834311+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:15:32.534441+02	t	\N	4	{}	{}	6	t	\N	\N
2	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2026-09-11 11:15:32.964596+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2026-09-11 11:15:33.094024+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	1	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	1	fs	1.2.0
2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	std	7.0.0
2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	2	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	2	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	3	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	3	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	4	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	4	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	5	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	5	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	6	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	6	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	7	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	7	std	8.7.4
6e6c04f7-6582-452b-9f49-84cf2f406b27	8	fs	1.2.0
6e6c04f7-6582-452b-9f49-84cf2f406b27	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	discovery::Discovered[myagent,name=discovered]	{}	2026-09-11 11:15:33.102307+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
6e6c04f7-6582-452b-9f49-84cf2f406b27	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-09-11 11:15:33.102329+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
b159b3c7-0372-49b0-9347-e531bf1e6536	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	2026-09-11 11:15:32.95277+02	6	0	{"28ff1a18-bea9-5d6a-9918-4c1d97d490d4": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "2da7108b-1afa-55e3-a230-815f3fca289b": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "53e64f05-634d-5767-9d88-e9515f6611e7": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "7a44a093-ec4b-5917-8f20-f4ce3591d2c1": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "89e07e62-c7c8-59f9-bd52-7a5ba6c90313": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "fde0bca1-b85b-523c-a154-0e46dadb089b": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
73cb3ae7-f0e9-4ed6-b1de-8c2b0ef90a85	dev-4	36e44c9f-4980-4720-87c9-ee38f2c59b75			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
6e6c04f7-6582-452b-9f49-84cf2f406b27	dev-1	36e44c9f-4980-4720-87c9-ee38f2c59b75			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
2c27f7f5-7be2-49ab-9e15-4f4f533be175	dev-1-twin	36e44c9f-4980-4720-87c9-ee38f2c59b75			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
3d7a6f89-d034-4234-8cf7-4217cb1cbf11	dev-2	36e44c9f-4980-4720-87c9-ee38f2c59b75			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	dev-3	36e44c9f-4980-4720-87c9-ee38f2c59b75			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.4	6e6c04f7-6582-452b-9f49-84cf2f406b27	\N	\N	\N	package
fs	1.2.0	6e6c04f7-6582-452b-9f49-84cf2f406b27	\N	\N	\N	package
std	7.0.0	2c27f7f5-7be2-49ab-9e15-4f4f533be175	\N	\N	\N	package
fs	1.2.0	2c27f7f5-7be2-49ab-9e15-4f4f533be175	\N	\N	\N	package
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
567819a3-3318-45d5-9fe0-a7253668527f	73cb3ae7-f0e9-4ed6-b1de-8c2b0ef90a85	2026-09-11 11:15:33.253689+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/bd6f5e95-781a-4f90-a688-8bac094f3832	f	f	bd6f5e95-781a-4f90-a688-8bac094f3832
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
754a4a01-672e-4a8e-a48e-57c26dc434f3	fact1	value1	6e6c04f7-6582-452b-9f49-84cf2f406b27	std::testing::NullResource[localhost,name=test1]	fact	2026-09-11 11:15:18.881101+02	{}	f
5f515587-0117-4e55-a00e-7c36a9cfdd93	fact2	value2	6e6c04f7-6582-452b-9f49-84cf2f406b27	std::testing::NullResource[localhost,name=test2]	fact	2026-09-11 11:15:18.883963+02	{}	t
16c8eb2b-6065-4f2d-9769-09b4b5d4c11a	fact3	value3	6e6c04f7-6582-452b-9f49-84cf2f406b27	std::testing::NullResource[localhost,name=test3]	fact	2026-09-11 11:15:18.886216+02	{}	t
3e06ae24-fab9-49f4-9a82-372f8083b967	parameter1	value1	6e6c04f7-6582-452b-9f49-84cf2f406b27		fact	2026-09-11 11:15:18.888881+02	{}	f
e8f644c1-b02e-4eb0-bb5e-eed93a77ccc8	parameter2	value2	6e6c04f7-6582-452b-9f49-84cf2f406b27		fact	2026-09-11 11:15:18.891169+02	{}	f
8ab38c8a-4bca-4e25-990e-8ce09436aed6	parameter3	value3	6e6c04f7-6582-452b-9f49-84cf2f406b27		fact	2026-09-11 11:15:18.893326+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
36e44c9f-4980-4720-87c9-ee38f2c59b75	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
8968bfba-bd86-4512-afd1-c6f4aa7a4a59	2026-09-11 11:14:47.117838+02	2026-09-11 11:14:47.120459+02		Init		Using extra environment variables during compile \n	0	f7ac53d5-703f-4be4-b429-730ca79d4895
b1be0948-6901-44ec-8abd-84af97e58032	2026-09-11 11:14:47.120764+02	2026-09-11 11:14:47.129635+02		Venv check		Creating new venv at /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env-py3.13\n	0	f7ac53d5-703f-4be4-b429-730ca79d4895
6c6d672e-5e41-49a7-bba0-5dda219c68ee	2026-09-11 11:14:47.131416+02	2026-09-11 11:14:47.4309+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	f7ac53d5-703f-4be4-b429-730ca79d4895
e5aa4ca5-9294-4969-8543-60b3654abcd9	2026-09-11 11:14:47.43141+02	2026-09-11 11:15:01.211516+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmph6gytxsq:\n                                 Pip command: /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmph6gytxsq inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, build, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	f7ac53d5-703f-4be4-b429-730ca79d4895
7c62b58d-4fbd-4474-a542-75a2616650b9	2026-09-11 11:15:15.765024+02	2026-09-11 11:15:15.767226+02		Init		Using extra environment variables during compile \n	0	da2dcb7a-78ed-48c3-89c8-07866bb7d145
54b337a9-34f5-42ba-ab53-9ab76ee08ae1	2026-09-11 11:15:15.767532+02	2026-09-11 11:15:15.768045+02		Venv check		Found existing venv\n	0	da2dcb7a-78ed-48c3-89c8-07866bb7d145
f9c9b7d0-422f-48ae-96ff-e8d372d0eb6c	2026-09-11 11:15:01.21278+02	2026-09-11 11:15:02.127288+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp8_eyj2oi --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.063 seconds\n	0	f7ac53d5-703f-4be4-b429-730ca79d4895
e5e0e2fb-89c2-4722-8b91-ed21a0d33172	2026-09-11 11:15:02.39642+02	2026-09-11 11:15:02.40405+02		Init		Using extra environment variables during compile \n	0	bad8c95a-a948-4a96-927b-4319aa841848
e0cd1754-12f4-4a18-bda4-fd7a8771b390	2026-09-11 11:15:02.405199+02	2026-09-11 11:15:02.432456+02		Venv check		Creating new venv at /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env-py3.13\n	0	bad8c95a-a948-4a96-927b-4319aa841848
b42c139e-0900-436d-891e-083c7206ad96	2026-09-11 11:15:18.927991+02	2026-09-11 11:15:18.930048+02		Init		Using extra environment variables during compile \n	0	b986bebd-52ca-488d-864c-efdfaee36706
238df253-ea29-400c-b817-ef81f50a203b	2026-09-11 11:15:02.436387+02	2026-09-11 11:15:02.762238+02	/tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	bad8c95a-a948-4a96-927b-4319aa841848
70257be9-6255-4d3d-bf22-39b7ed813ad4	2026-09-11 11:15:18.930259+02	2026-09-11 11:15:18.930642+02		Venv check		Found existing venv\n	0	b986bebd-52ca-488d-864c-efdfaee36706
3fed4fd3-99ff-45c4-94ac-70665590163e	2026-09-11 11:15:02.762918+02	2026-09-11 11:15:14.636908+02	/tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp0cdpjkov:\n                                 Pip command: /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp0cdpjkov inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, build, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	bad8c95a-a948-4a96-927b-4319aa841848
4faa02d3-aacd-4f12-b20d-9386f51991a2	2026-09-11 11:15:14.637621+02	2026-09-11 11:15:15.569269+02	/tmp/tmpv7_cins2/server/2c27f7f5-7be2-49ab-9e15-4f4f533be175/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 2c27f7f5-7be2-49ab-9e15-4f4f533be175 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyhp4ymaw --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	bad8c95a-a948-4a96-927b-4319aa841848
1daadd49-aaf0-4c99-947d-31852e073b90	2026-09-11 11:15:16.788982+02	2026-09-11 11:15:16.791365+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	c6164f82-a9f4-4e89-afad-7d9d0d32ebfa
b15d7706-3b0d-42db-ab10-eefa8b95db9b	2026-09-11 11:15:16.791597+02	2026-09-11 11:15:16.792048+02		Venv check		Found existing venv\n	0	c6164f82-a9f4-4e89-afad-7d9d0d32ebfa
25af22c2-5970-4062-b353-4c90d6bfa6d7	2026-09-11 11:15:15.768356+02	2026-09-11 11:15:16.685432+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpa0jau6q1 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	da2dcb7a-78ed-48c3-89c8-07866bb7d145
d4c8a80b-c7bf-48c2-91f0-e39c390b41c1	2026-09-11 11:15:17.926994+02	2026-09-11 11:15:17.931802+02		Init		Using extra environment variables during compile \n	0	928dad06-ef8b-438d-96e0-f89220e8c283
3ec4b4fb-a23a-4469-b138-b867dd27d6ea	2026-09-11 11:15:17.932047+02	2026-09-11 11:15:17.932493+02		Venv check		Found existing venv\n	0	928dad06-ef8b-438d-96e0-f89220e8c283
27604658-7731-4cfa-b24b-f9777ac1517d	2026-09-11 11:15:16.792246+02	2026-09-11 11:15:17.676567+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmptoa8ca0h --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.007 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	c6164f82-a9f4-4e89-afad-7d9d0d32ebfa
d3f8876b-2b1d-4175-8e2b-f719f163c897	2026-09-11 11:15:19.946797+02	2026-09-11 11:15:20.243782+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	a344e723-96c2-42e3-8e54-cab93a31c5af
f4726283-931b-4849-85bf-ab5f70feb7ba	2026-09-11 11:15:17.93268+02	2026-09-11 11:15:18.826004+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp_x71pi7t --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.014 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.061 seconds\n	0	928dad06-ef8b-438d-96e0-f89220e8c283
10b3187f-8e52-4a0f-9f57-46ee4a33d425	2026-09-11 11:15:19.931637+02	2026-09-11 11:15:19.939527+02		Init		Using extra environment variables during compile \n	0	a344e723-96c2-42e3-8e54-cab93a31c5af
ea8758c7-3d88-4a24-870a-2dabad22a0e4	2026-09-11 11:15:19.94054+02	2026-09-11 11:15:19.942691+02		Venv check		Found existing venv\n	0	a344e723-96c2-42e3-8e54-cab93a31c5af
eb545cbf-5956-4ea2-9576-d6369b21166b	2026-09-11 11:15:18.930805+02	2026-09-11 11:15:19.825279+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpf80krg39 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.055 seconds\n	0	b986bebd-52ca-488d-864c-efdfaee36706
6610f1db-9d9d-47d5-99fb-112e4015f79b	2026-09-11 11:15:20.24473+02	2026-09-11 11:15:31.460543+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpjflvpit4:\n                                 Pip command: /tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpjflvpit4 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.13/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.13/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.13/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	a344e723-96c2-42e3-8e54-cab93a31c5af
9afc08f7-87be-41c9-a998-9675cd0ae870	2026-09-11 11:15:31.461216+02	2026-09-11 11:15:32.389287+02	/tmp/tmpv7_cins2/server/6e6c04f7-6582-452b-9f49-84cf2f406b27/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6e6c04f7-6582-452b-9f49-84cf2f406b27 --server_address localhost --server_port 53689 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmph1dcpmic --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:53689/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:53689/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.052 seconds\n	0	a344e723-96c2-42e3-8e54-cab93a31c5af
933508dd-8b75-496e-8c1c-6e3563337682	2026-09-11 11:15:33.23814+02	2026-09-11 11:15:33.245065+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpv7_cins2/server/73cb3ae7-f0e9-4ed6-b1de-8c2b0ef90a85/compiler and no repository set.\n	1	bd6f5e95-781a-4f90-a688-8bac094f3832
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	9c22a6ce-100f-40b3-a4d8-af92fe85bf18
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	9c22a6ce-100f-40b3-a4d8-af92fe85bf18
2c27f7f5-7be2-49ab-9e15-4f4f533be175	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	fd58bbae-a6f3-46d3-9404-9927d56c908b
2c27f7f5-7be2-49ab-9e15-4f4f533be175	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	fd58bbae-a6f3-46d3-9404-9927d56c908b
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	455e05ac-432f-4ee1-8778-f7275c6a9fda
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	455e05ac-432f-4ee1-8778-f7275c6a9fda
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	00658d81-5cee-4005-a02f-7fc260a09c60
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	00658d81-5cee-4005-a02f-7fc260a09c60
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	00658d81-5cee-4005-a02f-7fc260a09c60
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	d6d37545-0f0e-4dd9-8127-00b249f1c142
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d6d37545-0f0e-4dd9-8127-00b249f1c142
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	3990d892-26f1-4579-a6bc-7629a977f313
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3990d892-26f1-4579-a6bc-7629a977f313
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	f90cebde-7947-4be4-b19b-d716e6d06604
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	f90cebde-7947-4be4-b19b-d716e6d06604
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	c58af263-1aa1-4d8e-91f1-cb0aa9e47cdc
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	c58af263-1aa1-4d8e-91f1-cb0aa9e47cdc
6e6c04f7-6582-452b-9f49-84cf2f406b27	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	d3122ebd-8696-44cc-b610-c1454da7af91
6e6c04f7-6582-452b-9f49-84cf2f406b27	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	36128c7a-f75c-4252-99ad-4acf1f4d395e
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	ea8c2a85-e40e-4494-88be-13b8829f10df
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ea8c2a85-e40e-4494-88be-13b8829f10df
6e6c04f7-6582-452b-9f49-84cf2f406b27	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	3e53ed7b-6a42-4fdc-b9b0-9294a811350a
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	fb81c677-b944-4bf0-971b-59fecc99ed1d
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
4609ca0b-9f2c-4027-92fb-d56cee69b04e	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-09-11 11:15:33.038764+02
bf034c93-8e63-44c0-a9c7-ce841776ed90	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-09-11 11:15:33.057139+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-09-11 11:15:32.837796+02	\N	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key10]	2026-09-11 11:15:33.038764+02	\N	2026-09-11 11:15:33.038764+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.975246+02	f	4609ca0b-9f2c-4027-92fb-d56cee69b04e	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	std::AgentConfig[internal,agentname=localhost]	2026-09-11 11:15:02.25447+02	\N	2026-09-11 11:15:02.25447+02	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:02.23434+02	f	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-09-11 11:15:32.837796+02	\N	\N	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test]	2026-09-11 11:15:02.259709+02	\N	2026-09-11 11:15:02.259709+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:02.23434+02	f	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key7]	2026-09-11 11:15:33.05289+02	2026-09-11 11:15:33.044341+02	2026-09-11 11:15:33.05289+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.975246+02	t	\N	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	std::AgentConfig[internal,agentname=localhost]	2026-09-11 11:15:15.634306+02	\N	2026-09-11 11:15:15.634306+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:15.627812+02	f	\N	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	fs::File[localhost,path=/tmp/test]	2026-09-11 11:15:15.637797+02	\N	2026-09-11 11:15:15.637797+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:15.627812+02	f	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key1]	2026-09-11 11:15:32.863365+02	2026-09-11 11:15:32.859349+02	2026-09-11 11:15:32.863365+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.837796+02	t	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key11]	2026-09-11 11:15:33.057139+02	\N	2026-09-11 11:15:33.057139+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.975246+02	f	bf034c93-8e63-44c0-a9c7-ce841776ed90	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Fail[agent1,key=key2]	2026-09-11 11:15:32.866249+02	\N	2026-09-11 11:15:32.866249+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:32.837796+02	f	\N	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	fs::File[localhost,path=/tmp/test_orphan]	2026-09-11 11:15:17.793603+02	\N	2026-09-11 11:15:17.793603+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:17.782285+02	f	\N	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key3]	2026-09-11 11:15:32.868343+02	\N	2026-09-11 11:15:32.868343+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-09-11 11:15:32.837796+02	f	\N	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	test::Resource[agent2,key=key2]	2026-09-11 11:15:32.567726+02	\N	2026-09-11 11:15:32.567726+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:32.5601+02	f	\N	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	test::Resource[agent3,key=key3]	2026-09-11 11:15:32.56968+02	\N	2026-09-11 11:15:32.56968+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-09-11 11:15:32.5601+02	f	\N	7
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key9]	2026-09-11 11:15:33.061037+02	2026-09-11 11:15:33.058083+02	2026-09-11 11:15:33.061037+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.975246+02	t	\N	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	test::Resource[agent1,key=key6]	2026-09-11 11:15:32.857984+02	2026-09-11 11:15:32.842795+02	2026-09-11 11:15:32.857984+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 11:15:32.837796+02	t	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	9c22a6ce-100f-40b3-a4d8-af92fe85bf18	\N
2c27f7f5-7be2-49ab-9e15-4f4f533be175	fd58bbae-a6f3-46d3-9404-9927d56c908b	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	455e05ac-432f-4ee1-8778-f7275c6a9fda	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	00658d81-5cee-4005-a02f-7fc260a09c60	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	d6d37545-0f0e-4dd9-8127-00b249f1c142	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	3990d892-26f1-4579-a6bc-7629a977f313	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	f90cebde-7947-4be4-b19b-d716e6d06604	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	c58af263-1aa1-4d8e-91f1-cb0aa9e47cdc	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	d3122ebd-8696-44cc-b610-c1454da7af91	set-b
6e6c04f7-6582-452b-9f49-84cf2f406b27	36128c7a-f75c-4252-99ad-4acf1f4d395e	set-a
6e6c04f7-6582-452b-9f49-84cf2f406b27	ea8c2a85-e40e-4494-88be-13b8829f10df	\N
6e6c04f7-6582-452b-9f49-84cf2f406b27	3e53ed7b-6a42-4fdc-b9b0-9294a811350a	set-a
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	8de0222f-db77-4820-a510-f69c78b14fd4	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	82f14ebd-357d-4b8b-8c46-7cd69b109f73	\N
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	fb81c677-b944-4bf0-971b-59fecc99ed1d	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	1	9c22a6ce-100f-40b3-a4d8-af92fe85bf18
2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	fd58bbae-a6f3-46d3-9404-9927d56c908b
6e6c04f7-6582-452b-9f49-84cf2f406b27	2	455e05ac-432f-4ee1-8778-f7275c6a9fda
6e6c04f7-6582-452b-9f49-84cf2f406b27	3	00658d81-5cee-4005-a02f-7fc260a09c60
6e6c04f7-6582-452b-9f49-84cf2f406b27	4	d6d37545-0f0e-4dd9-8127-00b249f1c142
6e6c04f7-6582-452b-9f49-84cf2f406b27	5	3990d892-26f1-4579-a6bc-7629a977f313
6e6c04f7-6582-452b-9f49-84cf2f406b27	6	f90cebde-7947-4be4-b19b-d716e6d06604
6e6c04f7-6582-452b-9f49-84cf2f406b27	7	c58af263-1aa1-4d8e-91f1-cb0aa9e47cdc
6e6c04f7-6582-452b-9f49-84cf2f406b27	7	d3122ebd-8696-44cc-b610-c1454da7af91
6e6c04f7-6582-452b-9f49-84cf2f406b27	7	36128c7a-f75c-4252-99ad-4acf1f4d395e
6e6c04f7-6582-452b-9f49-84cf2f406b27	8	ea8c2a85-e40e-4494-88be-13b8829f10df
6e6c04f7-6582-452b-9f49-84cf2f406b27	8	3e53ed7b-6a42-4fdc-b9b0-9294a811350a
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	8de0222f-db77-4820-a510-f69c78b14fd4
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	82f14ebd-357d-4b8b-8c46-7cd69b109f73
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	3	fb81c677-b944-4bf0-971b-59fecc99ed1d
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
20a30452-8b5c-4b5e-b75a-51a0b04064cb	store	2026-09-11 11:15:02.110861+02	2026-09-11 11:15:02.117621+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T11:15:02.117631+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
c4a65932-fdfb-4d8d-9c9a-3cfd19dd41ce	deploy	2026-09-11 11:15:02.244581+02	2026-09-11 11:15:02.25447+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:02.253571+02:00\\"}"}	unavailable	\N	nochange	6e6c04f7-6582-452b-9f49-84cf2f406b27	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
970c3fd5-fb2f-4a69-8ee0-b15d10dede4f	deploy	2026-09-11 11:15:02.2585+02	2026-09-11 11:15:02.259709+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:02.259273+02:00\\"}"}	unavailable	\N	nochange	6e6c04f7-6582-452b-9f49-84cf2f406b27	1	{"fs::File[localhost,path=/tmp/test],v=1"}
d16eb0a0-45df-4e5b-93f5-4c21f4e8b7f7	store	2026-09-11 11:15:15.55725+02	2026-09-11 11:15:15.562913+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T11:15:15.562923+02:00\\"}"}	\N	\N	\N	2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
c7ca440d-8087-4400-b329-229daf935c7e	deploy	2026-09-11 11:15:15.632739+02	2026-09-11 11:15:15.634306+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:15.633814+02:00\\"}"}	unavailable	\N	nochange	2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
9928f6f3-efe1-4aa7-9229-1fb9cd5f1728	deploy	2026-09-11 11:15:15.636696+02	2026-09-11 11:15:15.637797+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:15.637381+02:00\\"}"}	unavailable	\N	nochange	2c27f7f5-7be2-49ab-9e15-4f4f533be175	1	{"fs::File[localhost,path=/tmp/test],v=1"}
628676a7-9635-4ac9-87b8-8c1efb41d5c1	store	2026-09-11 11:15:16.677035+02	2026-09-11 11:15:16.679662+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-11T11:15:16.679670+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
d62b9ba8-aa89-4022-b975-342873034d1d	store	2026-09-11 11:15:17.667409+02	2026-09-11 11:15:17.66992+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-11T11:15:17.669928+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	3	{"std::AgentConfig[internal,agentname=localhost],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
829da6dc-2d84-4757-b8ba-482f47454a9f	deploy	2026-09-11 11:15:17.786246+02	2026-09-11 11:15:17.793603+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-09-11T11:15:17.793081+02:00\\"}"}	unavailable	\N	nochange	6e6c04f7-6582-452b-9f49-84cf2f406b27	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
c7744e73-ea03-4914-92e2-20a63319657f	store	2026-09-11 11:15:18.814495+02	2026-09-11 11:15:18.819734+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-09-11T11:15:18.819746+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	4	{"fs::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
05c59cac-97a9-48fe-a762-7e71f918c3f3	store	2026-09-11 11:15:19.816248+02	2026-09-11 11:15:19.818662+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-09-11T11:15:19.818671+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	5	{"fs::File[localhost,path=/tmp/test],v=5","std::AgentConfig[internal,agentname=localhost],v=5"}
8580ca1d-1555-4acf-94c4-17453870e78e	store	2026-09-11 11:15:32.380612+02	2026-09-11 11:15:32.383046+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-09-11T11:15:32.383054+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	6	{"fs::File[localhost,path=/tmp/test],v=6","std::AgentConfig[internal,agentname=localhost],v=6"}
b2275548-5939-489d-85bc-f8d94815b43e	store	2026-09-11 11:15:32.534357+02	2026-09-11 11:15:32.538629+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-09-11T11:15:32.538637+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	7	{"std::AgentConfig[internal,agentname=localhost],v=7","test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7"}
76da0c82-5348-4698-8a47-eb01ff7133b9	deploy	2026-09-11 11:15:32.565839+02	2026-09-11 11:15:32.567726+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.567077+02:00\\"}"}	unavailable	\N	nochange	6e6c04f7-6582-452b-9f49-84cf2f406b27	7	{"test::Resource[agent2,key=key2],v=7"}
a544bce5-20c9-44e3-919f-efb925f7ac31	deploy	2026-09-11 11:15:32.56779+02	2026-09-11 11:15:32.56968+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.569168+02:00\\"}"}	unavailable	\N	nochange	6e6c04f7-6582-452b-9f49-84cf2f406b27	7	{"test::Resource[agent3,key=key3],v=7"}
a4ca006d-35f7-4678-b375-4c5b22145550	store	2026-09-11 11:15:32.683976+02	2026-09-11 11:15:32.687845+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-09-11T11:15:32.687853+02:00\\"}"}	\N	\N	\N	6e6c04f7-6582-452b-9f49-84cf2f406b27	8	{"std::AgentConfig[internal,agentname=localhost],v=8","fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
e5edfe16-1504-47e4-8250-70c36a3cf65d	dryrun	2026-09-11 11:15:32.961307+02	2026-09-11 11:15:32.961549+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.961351+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536 - duration 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0001480579376220703, \\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.961537+02:00\\"}"}	dry	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key1],v=1"}
b9597908-1c24-4dbd-b32b-3d964aecbb15	dryrun	2026-09-11 11:15:32.965072+02	2026-09-11 11:15:32.965659+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.965134+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.000446319580078125, \\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.965638+02:00\\"}"}	dry	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key3],v=1"}
ef2c33e0-dd09-4c92-bb48-72053862ae14	dryrun	2026-09-11 11:15:32.967987+02	2026-09-11 11:15:32.968351+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.968049+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00023055076599121094, \\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.968334+02:00\\"}"}	dry	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key5],v=1"}
3a7ceea9-4f2a-4b77-8a91-132cefddfa2f	dryrun	2026-09-11 11:15:32.970463+02	2026-09-11 11:15:32.970792+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.970522+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002105236053466797, \\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.970777+02:00\\"}"}	dry	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key6],v=1"}
780c15ba-bc8c-4ec1-b165-92e8afe36dd3	deploy	2026-09-11 11:15:33.019555+02	2026-09-11 11:15:33.038764+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 97b11d38-cd11-4946-bdc2-4e945efa89ae).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"97b11d38-cd11-4946-bdc2-4e945efa89ae\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.026373+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.027047+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 97b11d38-cd11-4946-bdc2-4e945efa89ae) - duration: 0.0121 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.012098312377929688, \\"deploy_id\\": \\"97b11d38-cd11-4946-bdc2-4e945efa89ae\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.038640+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	{"test::Resource[agent1,key=key10],v=2"}
b39b85d8-66f6-4ab3-ad5b-6a8e5579ea66	deploy	2026-09-11 11:15:33.044446+02	2026-09-11 11:15:33.05289+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3ec1fd9b-79aa-40b8-a47f-40606e005259).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"3ec1fd9b-79aa-40b8-a47f-40606e005259\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.047335+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 3ec1fd9b-79aa-40b8-a47f-40606e005259) - duration: 0.0054 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.005430459976196289, \\"deploy_id\\": \\"3ec1fd9b-79aa-40b8-a47f-40606e005259\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.052858+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	{"test::Resource[agent1,key=key7],v=2"}
65a8cc89-6d3e-4363-8bc6-7e194a503254	store	2026-09-11 11:15:32.834264+02	2026-09-11 11:15:32.835923+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T11:15:32.835931+02:00\\"}"}	\N	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key3],v=1"}
61b04529-77ca-46a0-9b15-46320befd756	deploy	2026-09-11 11:15:32.842839+02	2026-09-11 11:15:32.857984+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 9fa68f67-35b4-4b17-b10b-8caeaeb584f9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"9fa68f67-35b4-4b17-b10b-8caeaeb584f9\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.851876+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 9fa68f67-35b4-4b17-b10b-8caeaeb584f9) - duration: 0.0060 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0060002803802490234, \\"deploy_id\\": \\"9fa68f67-35b4-4b17-b10b-8caeaeb584f9\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.857939+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key6],v=1"}
022a5828-17cc-4b92-865c-a0cb8d90483f	deploy	2026-09-11 11:15:32.859383+02	2026-09-11 11:15:32.863365+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 05712b86-da5c-4cd7-b0ea-cf64dfd17cb0).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"05712b86-da5c-4cd7-b0ea-cf64dfd17cb0\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.860264+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 05712b86-da5c-4cd7-b0ea-cf64dfd17cb0) - duration: 0.0030 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.003020763397216797, \\"deploy_id\\": \\"05712b86-da5c-4cd7-b0ea-cf64dfd17cb0\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.863330+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key1],v=1"}
7f74980b-029a-4ebd-a20f-2b75bdce02b2	deploy	2026-09-11 11:15:32.864336+02	2026-09-11 11:15:32.866249+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ee8fb1ea-121c-455e-8fe4-e60b4aca76ac).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"ee8fb1ea-121c-455e-8fe4-e60b4aca76ac\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.865152+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2644, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.865752+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: ee8fb1ea-121c-455e-8fe4-e60b4aca76ac) - duration: 0.0010 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0010368824005126953, \\"deploy_id\\": \\"ee8fb1ea-121c-455e-8fe4-e60b4aca76ac\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.866226+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Fail[agent1,key=key2],v=1"}
941a5315-ec28-4fa1-8121-0f1f71ba4e8e	deploy	2026-09-11 11:15:32.867329+02	2026-09-11 11:15:32.868343+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 6879da7d-1ebc-4269-8d89-3ec2c15d07db).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"6879da7d-1ebc-4269-8d89-3ec2c15d07db\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.868146+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.868245+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 6879da7d-1ebc-4269-8d89-3ec2c15d07db) - duration: 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00014019012451171875, \\"deploy_id\\": \\"6879da7d-1ebc-4269-8d89-3ec2c15d07db\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.868321+02:00\\"}"}	skipped	\N	nochange	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Resource[agent1,key=key3],v=1"}
bff089df-4623-4528-8348-2a217b90c753	dryrun	2026-09-11 11:15:32.955888+02	2026-09-11 11:15:32.956512+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.955966+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: b159b3c7-0372-49b0-9347-e531bf1e6536 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0004570484161376953, \\"dry_run_id\\": \\"b159b3c7-0372-49b0-9347-e531bf1e6536\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-11T11:15:32.956491+02:00\\"}"}	dry	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	1	{"test::Fail[agent1,key=key2],v=1"}
ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	store	2026-09-11 11:15:32.964449+02	2026-09-11 11:15:32.972913+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-11T11:15:32.972920+02:00\\"}"}	\N	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	{"test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key10],v=2","test::Fail[agent1,key=key2],v=2"}
409ecde6-c41d-4869-b30e-1d7c5244363f	store	2026-09-11 11:15:33.09397+02	2026-09-11 11:15:33.095908+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-11T11:15:33.095916+02:00\\"}"}	\N	\N	\N	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	3	{"test::Resource[agent1,key=key1],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key5],v=3"}
4e13fd80-01b2-41cb-8075-791c74c86881	deploy	2026-09-11 11:15:33.054007+02	2026-09-11 11:15:33.057139+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 6c8f5630-eaaa-45e2-8041-66966813705a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"6c8f5630-eaaa-45e2-8041-66966813705a\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.054624+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.054812+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 6c8f5630-eaaa-45e2-8041-66966813705a) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.0024421215057373047, \\"deploy_id\\": \\"6c8f5630-eaaa-45e2-8041-66966813705a\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.057106+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	{"test::Resource[agent1,key=key11],v=2"}
cfc34e60-e433-4fa5-ac92-8df1d840e33d	deploy	2026-09-11 11:15:33.05811+02	2026-09-11 11:15:33.061037+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 45a75266-9a78-40f9-bc9a-eea5814fb4d3).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"45a75266-9a78-40f9-bc9a-eea5814fb4d3\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.058685+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 45a75266-9a78-40f9-bc9a-eea5814fb4d3) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0022869110107421875, \\"deploy_id\\": \\"45a75266-9a78-40f9-bc9a-eea5814fb4d3\\"}, \\"timestamp\\": \\"2026-09-11T11:15:33.061010+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2	{"test::Resource[agent1,key=key9],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
6e6c04f7-6582-452b-9f49-84cf2f406b27	20a30452-8b5c-4b5e-b75a-51a0b04064cb	fs::File[localhost,path=/tmp/test]	1
6e6c04f7-6582-452b-9f49-84cf2f406b27	20a30452-8b5c-4b5e-b75a-51a0b04064cb	std::AgentConfig[internal,agentname=localhost]	1
6e6c04f7-6582-452b-9f49-84cf2f406b27	c4a65932-fdfb-4d8d-9c9a-3cfd19dd41ce	std::AgentConfig[internal,agentname=localhost]	1
6e6c04f7-6582-452b-9f49-84cf2f406b27	970c3fd5-fb2f-4a69-8ee0-b15d10dede4f	fs::File[localhost,path=/tmp/test]	1
2c27f7f5-7be2-49ab-9e15-4f4f533be175	d16eb0a0-45df-4e5b-93f5-4c21f4e8b7f7	fs::File[localhost,path=/tmp/test]	1
2c27f7f5-7be2-49ab-9e15-4f4f533be175	d16eb0a0-45df-4e5b-93f5-4c21f4e8b7f7	std::AgentConfig[internal,agentname=localhost]	1
2c27f7f5-7be2-49ab-9e15-4f4f533be175	c7ca440d-8087-4400-b329-229daf935c7e	std::AgentConfig[internal,agentname=localhost]	1
2c27f7f5-7be2-49ab-9e15-4f4f533be175	9928f6f3-efe1-4aa7-9229-1fb9cd5f1728	fs::File[localhost,path=/tmp/test]	1
6e6c04f7-6582-452b-9f49-84cf2f406b27	628676a7-9635-4ac9-87b8-8c1efb41d5c1	std::AgentConfig[internal,agentname=localhost]	2
6e6c04f7-6582-452b-9f49-84cf2f406b27	628676a7-9635-4ac9-87b8-8c1efb41d5c1	fs::File[localhost,path=/tmp/test]	2
6e6c04f7-6582-452b-9f49-84cf2f406b27	d62b9ba8-aa89-4022-b975-342873034d1d	std::AgentConfig[internal,agentname=localhost]	3
6e6c04f7-6582-452b-9f49-84cf2f406b27	d62b9ba8-aa89-4022-b975-342873034d1d	fs::File[localhost,path=/tmp/test_orphan]	3
6e6c04f7-6582-452b-9f49-84cf2f406b27	d62b9ba8-aa89-4022-b975-342873034d1d	fs::File[localhost,path=/tmp/test]	3
6e6c04f7-6582-452b-9f49-84cf2f406b27	829da6dc-2d84-4757-b8ba-482f47454a9f	fs::File[localhost,path=/tmp/test_orphan]	3
6e6c04f7-6582-452b-9f49-84cf2f406b27	c7744e73-ea03-4914-92e2-20a63319657f	fs::File[localhost,path=/tmp/test]	4
6e6c04f7-6582-452b-9f49-84cf2f406b27	c7744e73-ea03-4914-92e2-20a63319657f	std::AgentConfig[internal,agentname=localhost]	4
6e6c04f7-6582-452b-9f49-84cf2f406b27	05c59cac-97a9-48fe-a762-7e71f918c3f3	fs::File[localhost,path=/tmp/test]	5
6e6c04f7-6582-452b-9f49-84cf2f406b27	05c59cac-97a9-48fe-a762-7e71f918c3f3	std::AgentConfig[internal,agentname=localhost]	5
6e6c04f7-6582-452b-9f49-84cf2f406b27	8580ca1d-1555-4acf-94c4-17453870e78e	fs::File[localhost,path=/tmp/test]	6
6e6c04f7-6582-452b-9f49-84cf2f406b27	8580ca1d-1555-4acf-94c4-17453870e78e	std::AgentConfig[internal,agentname=localhost]	6
6e6c04f7-6582-452b-9f49-84cf2f406b27	b2275548-5939-489d-85bc-f8d94815b43e	std::AgentConfig[internal,agentname=localhost]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	b2275548-5939-489d-85bc-f8d94815b43e	test::Resource[agent3,key=key3]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	b2275548-5939-489d-85bc-f8d94815b43e	fs::File[localhost,path=/tmp/test]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	b2275548-5939-489d-85bc-f8d94815b43e	test::Resource[agent2,key=key2]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	76da0c82-5348-4698-8a47-eb01ff7133b9	test::Resource[agent2,key=key2]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	a544bce5-20c9-44e3-919f-efb925f7ac31	test::Resource[agent3,key=key3]	7
6e6c04f7-6582-452b-9f49-84cf2f406b27	a4ca006d-35f7-4678-b375-4c5b22145550	std::AgentConfig[internal,agentname=localhost]	8
6e6c04f7-6582-452b-9f49-84cf2f406b27	a4ca006d-35f7-4678-b375-4c5b22145550	fs::File[localhost,path=/tmp/test]	8
6e6c04f7-6582-452b-9f49-84cf2f406b27	a4ca006d-35f7-4678-b375-4c5b22145550	test::Resource[agent2,key=key2]	8
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Resource[agent1,key=key4]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Resource[agent1,key=key1]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Resource[agent1,key=key6]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Resource[agent1,key=key5]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Fail[agent1,key=key2]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	65a8cc89-6d3e-4363-8bc6-7e194a503254	test::Resource[agent1,key=key3]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	61b04529-77ca-46a0-9b15-46320befd756	test::Resource[agent1,key=key6]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	022a5828-17cc-4b92-865c-a0cb8d90483f	test::Resource[agent1,key=key1]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	7f74980b-029a-4ebd-a20f-2b75bdce02b2	test::Fail[agent1,key=key2]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	941a5315-ec28-4fa1-8121-0f1f71ba4e8e	test::Resource[agent1,key=key3]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	bff089df-4623-4528-8348-2a217b90c753	test::Fail[agent1,key=key2]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	e5edfe16-1504-47e4-8250-70c36a3cf65d	test::Resource[agent1,key=key1]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	b9597908-1c24-4dbd-b32b-3d964aecbb15	test::Resource[agent1,key=key3]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ef2c33e0-dd09-4c92-bb48-72053862ae14	test::Resource[agent1,key=key5]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	3a7ceea9-4f2a-4b77-8a91-132cefddfa2f	test::Resource[agent1,key=key6]	1
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key9]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key3]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key4]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key7]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key1]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key11]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key5]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Resource[agent1,key=key10]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	ad21fe3d-0fd6-4882-80ee-3ab9bb34d3c1	test::Fail[agent1,key=key2]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	780c15ba-bc8c-4ec1-b165-92e8afe36dd3	test::Resource[agent1,key=key10]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	b39b85d8-66f6-4ab3-ad5b-6a8e5579ea66	test::Resource[agent1,key=key7]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	4e13fd80-01b2-41cb-8075-791c74c86881	test::Resource[agent1,key=key11]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	cfc34e60-e433-4fa5-ac92-8df1d840e33d	test::Resource[agent1,key=key9]	2
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key1]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Fail[agent1,key=key2]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key3]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key8]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key7]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key4]	3
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	409ecde6-c41d-4869-b30e-1d7c5244363f	test::Resource[agent1,key=key5]	3
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
2c27f7f5-7be2-49ab-9e15-4f4f533be175	1
6e6c04f7-6582-452b-9f49-84cf2f406b27	8
1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	6e6c04f7-6582-452b-9f49-84cf2f406b27	2026-09-11 11:14:46.843961+02	\N	8dc7890a-e0f2-43bf-ade5-84b26dc1e2c4
hugo-Latitude-5421	2c27f7f5-7be2-49ab-9e15-4f4f533be175	2026-09-11 11:14:46.961327+02	\N	1629cdb2-7ca2-4fdf-8555-60b0ccf05de0
hugo-Latitude-5421	1d13d752-1e04-4cac-b2d6-90a14a9d1ba1	2026-09-11 11:15:32.720593+02	2026-09-11 11:15:33.089807+02	8e649d55-af1b-4bca-9709-9e9a54c9ba06
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

