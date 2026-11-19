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
    inmanta_module_name character varying NOT NULL COLLATE pg_catalog."C",
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
    inmanta_module_name character varying NOT NULL COLLATE pg_catalog."C",
    inmanta_module_version character varying NOT NULL COLLATE pg_catalog."C",
    extras character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL
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
    resource_filter jsonb,
    context jsonb
);


--
-- Name: dryrun_resource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dryrun_resource (
    dryrun_id uuid NOT NULL,
    resource_id character varying NOT NULL,
    changes jsonb DEFAULT '{}'::jsonb NOT NULL,
    diff_status character varying
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
    name character varying NOT NULL COLLATE pg_catalog."C",
    version character varying NOT NULL COLLATE pg_catalog."C",
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
    inmanta_module_name character varying NOT NULL COLLATE pg_catalog."C",
    inmanta_module_version character varying NOT NULL COLLATE pg_catalog."C",
    environment uuid NOT NULL,
    file_content_hash character varying NOT NULL,
    path character varying NOT NULL COLLATE pg_catalog."C"
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
fe36bec6-932d-4537-b03c-27798f86fb9e	$__scheduler	f	\N
4503df51-663b-4ecb-8d50-5bca78087c61	$__scheduler	f	\N
24ce31d9-27e2-4940-82c3-6b45a085c63d	$__scheduler	f	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	localhost	f	\N
4503df51-663b-4ecb-8d50-5bca78087c61	localhost	f	\N
4503df51-663b-4ecb-8d50-5bca78087c61	internal	f	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	agent2	f	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	agent3	f	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	agent1	t	t
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	$__scheduler	t	t
ac629c48-2c92-430b-a856-db13352a697b	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
1	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
1	internal	std	4503df51-663b-4ecb-8d50-5bca78087c61
1	localhost	fs	4503df51-663b-4ecb-8d50-5bca78087c61
2	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
2	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
3	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
3	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
4	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
4	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
5	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
5	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
6	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
6	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
7	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
7	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
8	localhost	fs	fe36bec6-932d-4537-b03c-27798f86fb9e
8	localhost	std	fe36bec6-932d-4537-b03c-27798f86fb9e
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
ed92d805-3122-4fc9-aa0e-8ed705519301	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:11.076038+01	2026-11-19 08:47:27.335002+01	2026-11-19 08:47:11.068115+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	d2db8029-2550-48fc-975f-7a25426928e9	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
16a5ba77-c509-4bf2-9c32-5f1e4999614a	4503df51-663b-4ecb-8d50-5bca78087c61	2026-11-19 08:47:27.63225+01	2026-11-19 08:47:44.232607+01	2026-11-19 08:47:27.6129+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	9a64d268-26ff-446c-a3dd-1f28a18f4db6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
2c6faaec-2a61-4f51-a7b0-0f002426cbd9	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:44.492299+01	2026-11-19 08:47:45.392077+01	2026-11-19 08:47:44.479852+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	061e52f6-945b-4c5c-b6e5-4fb745f2eb01	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
7ad10c92-1992-4bcb-ae07-8483f4a5eb99	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:45.496074+01	2026-11-19 08:47:46.472146+01	2026-11-19 08:47:45.468637+01	{}	{"add_one_resource": "true"}	t	f	t	3	45d95fae-4c41-492b-9cdf-f37318ff164b	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
c162b0d8-f4b1-4412-a5e0-56deb6c32507	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:46.735799+01	2026-11-19 08:47:47.64188+01	2026-11-19 08:47:46.728302+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	64cd4b8a-f9f1-457b-a222-bbf105fd4ef3	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
67c3c66e-dbac-4199-a6cf-8592711cabd4	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:47.780694+01	2026-11-19 08:47:48.66943+01	2026-11-19 08:47:47.777178+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	36f3fb31-df54-41c1-ad70-be16d48efbe9	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
dad8bec6-fccc-43ac-a435-aa85c62876aa	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:48.809865+01	2026-11-19 08:48:02.012909+01	2026-11-19 08:47:48.795952+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	77e4f967-6547-4a31-a413-d7834c386992	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
cb8ef7c6-05e2-4286-bded-f5da07d7ffd9	ac629c48-2c92-430b-a856-db13352a697b	2026-11-19 08:48:03.051953+01	2026-11-19 08:48:03.059801+01	2026-11-19 08:48:03.037295+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	835fdac8-a3aa-4cb6-b79e-621d5bfa1d5c	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
3	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2026-11-19 08:48:02.914474+01	f	\N	7	\N	t	\N	\N
1	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:27.315425+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	4503df51-663b-4ecb-8d50-5bca78087c61	2026-11-19 08:47:44.222736+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:45.383872+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:46.459906+01	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:47.633608+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:48.660982+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:48:02.003067+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:48:02.140893+01	t	\N	3	6	t	\N	\N
8	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:48:02.329353+01	t	\N	2	7	t	\N	\N
1	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2026-11-19 08:48:02.608017+01	t	\N	6	\N	t	\N	\N
2	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2026-11-19 08:48:02.764136+01	t	\N	9	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	1	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	1	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	1	fs	1.2.0	{}
4503df51-663b-4ecb-8d50-5bca78087c61	1	mitogen	0.2.5	{}
4503df51-663b-4ecb-8d50-5bca78087c61	1	std	7.0.0	{}
4503df51-663b-4ecb-8d50-5bca78087c61	1	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	2	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	2	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	2	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	3	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	3	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	3	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	4	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	4	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	4	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	5	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	5	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	5	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	6	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	6	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	6	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	7	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	7	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	7	std	8.7.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	8	fs	1.2.0	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	8	mitogen	0.2.5	{}
fe36bec6-932d-4537-b03c-27798f86fb9e	8	std	8.7.5	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	discovery::Discovered[myagent,name=discovered]	{}	2026-11-19 08:48:02.918569+01	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
fe36bec6-932d-4537-b03c-27798f86fb9e	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-11-19 08:48:02.918589+01	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, resource_filter, context) FROM stdin;
c1f44931-4f10-4451-b95e-c7c5acb07ec2	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	2026-11-19 08:48:02.75608+01	6	\N	\N
\.


--
-- Data for Name: dryrun_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun_resource (dryrun_id, resource_id, changes, diff_status) FROM stdin;
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Resource[agent1,key=key4]	{}	undefined
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Fail[agent1,key=key2]	{"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}	\N
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Resource[agent1,key=key1]	{}	\N
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Resource[agent1,key=key3]	{"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}	\N
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Resource[agent1,key=key5]	{"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}	\N
c1f44931-4f10-4451-b95e-c7c5acb07ec2	test::Resource[agent1,key=key6]	{}	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
24ce31d9-27e2-4940-82c3-6b45a085c63d	dev-2	0fcccfe3-1845-4f90-b94f-8e05e67c2379			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
4503df51-663b-4ecb-8d50-5bca78087c61	dev-1-twin	0fcccfe3-1845-4f90-b94f-8e05e67c2379			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
ac629c48-2c92-430b-a856-db13352a697b	dev-4	0fcccfe3-1845-4f90-b94f-8e05e67c2379			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
fe36bec6-932d-4537-b03c-27798f86fb9e	dev-1	0fcccfe3-1845-4f90-b94f-8e05e67c2379			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	dev-3	0fcccfe3-1845-4f90-b94f-8e05e67c2379			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
mitogen	0.2.5	fe36bec6-932d-4537-b03c-27798f86fb9e	{}	f
std	8.7.5	fe36bec6-932d-4537-b03c-27798f86fb9e	{}	f
fs	1.2.0	fe36bec6-932d-4537-b03c-27798f86fb9e	{}	f
mitogen	0.2.5	4503df51-663b-4ecb-8d50-5bca78087c61	{}	f
std	7.0.0	4503df51-663b-4ecb-8d50-5bca78087c61	{}	f
fs	1.2.0	4503df51-663b-4ecb-8d50-5bca78087c61	{}	f
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
ddf5463d-6f73-4dab-a8f5-4f8c1f563377	ac629c48-2c92-430b-a856-db13352a697b	2026-11-19 08:48:03.065423+01	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/cb8ef7c6-05e2-4286-bded-f5da07d7ffd9	f	f	cb8ef7c6-05e2-4286-bded-f5da07d7ffd9
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
948c7a5a-9830-47cc-b8a1-1f914459c5b8	fact1	value1	fe36bec6-932d-4537-b03c-27798f86fb9e	std::testing::NullResource[localhost,name=test1]	fact	2026-11-19 08:47:47.747047+01	{}	f
6dc590c9-c606-49d6-845f-fc70c7fe2a87	fact2	value2	fe36bec6-932d-4537-b03c-27798f86fb9e	std::testing::NullResource[localhost,name=test2]	fact	2026-11-19 08:47:47.758763+01	{}	t
629e8466-0877-4a0b-b681-73a86e0652cd	fact3	value3	fe36bec6-932d-4537-b03c-27798f86fb9e	std::testing::NullResource[localhost,name=test3]	fact	2026-11-19 08:47:47.768636+01	{}	t
75290cb1-24e2-4951-b438-b77e01856af8	parameter1	value1	fe36bec6-932d-4537-b03c-27798f86fb9e		fact	2026-11-19 08:47:47.770858+01	{}	f
abee43e8-927b-441d-a014-dfdfcac61d45	parameter2	value2	fe36bec6-932d-4537-b03c-27798f86fb9e		fact	2026-11-19 08:47:47.773026+01	{}	f
3f37a07c-a138-4b25-8df9-742543d920e0	parameter3	value3	fe36bec6-932d-4537-b03c-27798f86fb9e		fact	2026-11-19 08:47:47.7752+01	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
0fcccfe3-1845-4f90-b94f-8e05e67c2379	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
460d9ba1-410f-4e4f-bf18-d1e737e9ffc3	2026-11-19 08:47:11.07644+01	2026-11-19 08:47:11.079102+01		Init		Using extra environment variables during compile \n	0	ed92d805-3122-4fc9-aa0e-8ed705519301
5ff8d6a8-4db9-4365-ba05-174136b2e4da	2026-11-19 08:47:11.079418+01	2026-11-19 08:47:11.09247+01		Venv check		Creating new venv at /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env-py3.14\n	0	ed92d805-3122-4fc9-aa0e-8ed705519301
d68b4a07-b1b5-4076-a2a7-e143eee69922	2026-11-19 08:47:11.09441+01	2026-11-19 08:47:11.431169+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	ed92d805-3122-4fc9-aa0e-8ed705519301
980adcf5-bc4a-4a94-9de2-14bf2d354e69	2026-11-19 08:47:49.142655+01	2026-11-19 08:48:01.111554+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpxzd6pz38:\n                                 Pip command: /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpxzd6pz38 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.9)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in ./.env/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in ./.env/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in ./.env/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.55)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in ./.env/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in ./.env/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in ./.env/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in ./.env/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in ./.env/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in ./.env/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	dad8bec6-fccc-43ac-a435-aa85c62876aa
4ab767b8-38ab-4656-a794-a9a370308bc4	2026-11-19 08:48:01.112523+01	2026-11-19 08:48:02.012565+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmprdznt93w --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.009 seconds\ncompiler       DEBUG   The entire export command took 0.048 seconds\n	0	dad8bec6-fccc-43ac-a435-aa85c62876aa
f91bf647-2a43-4c5c-8bd4-264efdc67443	2026-11-19 08:47:27.634245+01	2026-11-19 08:47:27.644556+01		Init		Using extra environment variables during compile \n	0	16a5ba77-c509-4bf2-9c32-5f1e4999614a
ea38dfe7-31b2-4b86-8be7-18b83337f243	2026-11-19 08:47:46.74057+01	2026-11-19 08:47:47.641555+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpismtc3d0 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.048 seconds\n	0	c162b0d8-f4b1-4412-a5e0-56deb6c32507
fdcdb87f-f28f-4784-8d28-3cb9d5476c85	2026-11-19 08:47:27.645788+01	2026-11-19 08:47:27.678701+01		Venv check		Creating new venv at /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env-py3.14\n	0	16a5ba77-c509-4bf2-9c32-5f1e4999614a
a68ad8c8-2f82-492b-84a6-07383b500232	2026-11-19 08:47:45.497847+01	2026-11-19 08:47:45.506143+01		Init		Using extra environment variables during compile add_one_resource='true'\n	0	7ad10c92-1992-4bcb-ae07-8483f4a5eb99
6a0bab8f-eb15-4448-a4fc-04c0674b1e2d	2026-11-19 08:47:27.681919+01	2026-11-19 08:47:28.002617+01	/tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	16a5ba77-c509-4bf2-9c32-5f1e4999614a
aff9d5aa-a6e8-4298-86bf-816a236aa61d	2026-11-19 08:47:11.43159+01	2026-11-19 08:47:26.408038+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp7_8meupq:\n                                 Pip command: /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp7_8meupq inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Collecting click<8.6,>=8.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl (126 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting email-validator<3,>=1 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl (2.0 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl (494 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Collecting graphql-core<3.4,>=3.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl (366 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl (86 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email-validator<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl (360 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (2.3 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Collecting typing-inspection>=0.4.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl (14 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl (396 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mypy-extensions>=0.3.0 (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl (5.1 kB)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.55-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pycparser (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl (62 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Collecting certifi>=2023.5.7 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl (135 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Collecting cross-web>=0.6.0 (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl (27 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl (348 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Collecting chardet<8,>=3.0.2 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached chardet-7.7.0-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.7 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Collecting markdown-it-py>=2.2.0 (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, tzdata, typing-inspection, tornado, SQLAlchemy, python-slugify, pydantic-core, pycparser, pip, mypy-extensions, more-itertools, mitogen, markdown-it-py, jsonpath-ng, graphql-core, dnspython, cross-web, click, chardet, certifi, strawberry-graphql, pydantic, email-validator, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.5\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspection\ninmanta.pip              DEBUG   Found existing installation: typing-inspection 0.4.4\ninmanta.pip              DEBUG   Not uninstalling typing-inspection at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspection'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.4\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 9.1.3\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.50.1\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pycparser\ninmanta.pip              DEBUG   Found existing installation: pycparser 3.11\ninmanta.pip              DEBUG   Not uninstalling pycparser at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pycparser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.2.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: mypy-extensions\ninmanta.pip              DEBUG   Found existing installation: mypy_extensions 1.1.0\ninmanta.pip              DEBUG   Not uninstalling mypy-extensions at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'mypy_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: markdown-it-py\ninmanta.pip              DEBUG   Found existing installation: markdown-it-py 4.2.0\ninmanta.pip              DEBUG   Not uninstalling markdown-it-py at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'markdown-it-py'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: graphql-core\ninmanta.pip              DEBUG   Found existing installation: graphql-core 3.3.0\ninmanta.pip              DEBUG   Not uninstalling graphql-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'graphql-core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.9.0\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cross-web\ninmanta.pip              DEBUG   Found existing installation: cross-web 0.7.0\ninmanta.pip              DEBUG   Not uninstalling cross-web at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cross-web'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.5.0\ninmanta.pip              DEBUG   Not uninstalling click at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 7.6.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2026.7.22\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.14.1\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 2.3.0\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.9 certifi-2026.10.23 chardet-7.7.0 click-8.5.1 cross-web-0.9.0 dnspython-2.9.2 email-validator-2.4.0 graphql-core-3.3.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.16.0 markdown-it-py-4.3.0 mitogen-0.3.55 more-itertools-11.2.1 mypy-extensions-1.2.0 pip-26.3 pycparser-3.12 pydantic-2.14.3 pydantic-core-2.50.4 python-slugify-9.2.0 strawberry-graphql-0.341.2 texttable-1.7.3 tornado-6.6.1 typing-inspection-0.4.5 tzdata-2026.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	ed92d805-3122-4fc9-aa0e-8ed705519301
7440efe1-aa90-4883-a891-13050025a3ee	2026-11-19 08:47:26.408449+01	2026-11-19 08:47:27.334483+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp7a6p2nqx --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.061 seconds\n	0	ed92d805-3122-4fc9-aa0e-8ed705519301
bcd48ec9-7b56-4593-bfae-7eacc0d9d60d	2026-11-19 08:47:45.50721+01	2026-11-19 08:47:45.509198+01		Venv check		Found existing venv\n	0	7ad10c92-1992-4bcb-ae07-8483f4a5eb99
e03d8c98-faa1-4b79-bcbd-d4f555a05b87	2026-11-19 08:47:28.003078+01	2026-11-19 08:47:43.317678+01	/tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmprvwcldnp:\n                                 Pip command: /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmprvwcldnp inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Collecting click<8.6,>=8.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl (126 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting email-validator<3,>=1 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl (2.0 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl (494 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Collecting graphql-core<3.4,>=3.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl (366 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl (86 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email-validator<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl (360 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (2.3 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Collecting typing-inspection>=0.4.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl (14 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl (396 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mypy-extensions>=0.3.0 (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl (5.1 kB)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.55-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pycparser (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl (62 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Collecting certifi>=2023.5.7 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl (135 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Collecting cross-web>=0.6.0 (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl (27 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl (348 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Collecting chardet<8,>=3.0.2 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached chardet-7.7.0-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (1.7 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Collecting markdown-it-py>=2.2.0 (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, tzdata, typing-inspection, tornado, SQLAlchemy, python-slugify, pydantic-core, pycparser, pip, mypy-extensions, more-itertools, mitogen, markdown-it-py, jsonpath-ng, graphql-core, dnspython, cross-web, click, chardet, certifi, strawberry-graphql, pydantic, email-validator, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.5\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspection\ninmanta.pip              DEBUG   Found existing installation: typing-inspection 0.4.4\ninmanta.pip              DEBUG   Not uninstalling typing-inspection at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspection'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.4\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 9.1.3\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.50.1\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pycparser\ninmanta.pip              DEBUG   Found existing installation: pycparser 3.11\ninmanta.pip              DEBUG   Not uninstalling pycparser at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pycparser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.2.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: mypy-extensions\ninmanta.pip              DEBUG   Found existing installation: mypy_extensions 1.1.0\ninmanta.pip              DEBUG   Not uninstalling mypy-extensions at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'mypy_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: markdown-it-py\ninmanta.pip              DEBUG   Found existing installation: markdown-it-py 4.2.0\ninmanta.pip              DEBUG   Not uninstalling markdown-it-py at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'markdown-it-py'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: graphql-core\ninmanta.pip              DEBUG   Found existing installation: graphql-core 3.3.0\ninmanta.pip              DEBUG   Not uninstalling graphql-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'graphql-core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.9.0\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cross-web\ninmanta.pip              DEBUG   Found existing installation: cross-web 0.7.0\ninmanta.pip              DEBUG   Not uninstalling cross-web at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cross-web'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.5.0\ninmanta.pip              DEBUG   Not uninstalling click at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: chardet\ninmanta.pip              DEBUG   Found existing installation: chardet 7.6.0\ninmanta.pip              DEBUG   Not uninstalling chardet at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'chardet'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2026.7.22\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.14.1\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 2.3.0\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.9 certifi-2026.10.23 chardet-7.7.0 click-8.5.1 cross-web-0.9.0 dnspython-2.9.2 email-validator-2.4.0 graphql-core-3.3.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.16.0 markdown-it-py-4.3.0 mitogen-0.3.55 more-itertools-11.2.1 mypy-extensions-1.2.0 pip-26.3 pycparser-3.12 pydantic-2.14.3 pydantic-core-2.50.4 python-slugify-9.2.0 strawberry-graphql-0.341.2 texttable-1.7.3 tornado-6.6.1 typing-inspection-0.4.5 tzdata-2026.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	16a5ba77-c509-4bf2-9c32-5f1e4999614a
eda2ac53-596d-4554-bdeb-c6be84663f98	2026-11-19 08:47:43.318513+01	2026-11-19 08:47:44.232244+01	/tmp/tmpgzuw8u_s/server/4503df51-663b-4ecb-8d50-5bca78087c61/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 4503df51-663b-4ecb-8d50-5bca78087c61 --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpnmd14od3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.049 seconds\n	0	16a5ba77-c509-4bf2-9c32-5f1e4999614a
e88560dd-5121-40fc-a364-222740b0ea67	2026-11-19 08:47:47.783612+01	2026-11-19 08:47:48.669089+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpxasyp62d --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.012 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	67c3c66e-dbac-4199-a6cf-8592711cabd4
c485bec6-772e-4d5d-a174-bb4419a65d21	2026-11-19 08:47:44.495215+01	2026-11-19 08:47:44.499637+01		Init		Using extra environment variables during compile \n	0	2c6faaec-2a61-4f51-a7b0-0f002426cbd9
7a5feef1-5b7e-43d1-8b2f-fc9859c6ccea	2026-11-19 08:47:45.51015+01	2026-11-19 08:47:46.471817+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmptcyuh8ic --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	7ad10c92-1992-4bcb-ae07-8483f4a5eb99
dff9e957-e7d5-41e0-842b-4fec46cb491d	2026-11-19 08:47:44.499851+01	2026-11-19 08:47:44.500269+01		Venv check		Found existing venv\n	0	2c6faaec-2a61-4f51-a7b0-0f002426cbd9
907a4f30-7376-4c86-8252-0b5a24353531	2026-11-19 08:47:44.500436+01	2026-11-19 08:47:45.391756+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m inmanta.app -vvv export -X -e fe36bec6-932d-4537-b03c-27798f86fb9e --server_address localhost --server_port 39213 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcaxvo6uu --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39213/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39213/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.049 seconds\n	0	2c6faaec-2a61-4f51-a7b0-0f002426cbd9
12dd302b-cf5e-4168-b8db-e398aae27bc9	2026-11-19 08:47:47.780963+01	2026-11-19 08:47:47.782869+01		Init		Using extra environment variables during compile \n	0	67c3c66e-dbac-4199-a6cf-8592711cabd4
2b600080-6381-43b9-ba0f-e4ca8ab18182	2026-11-19 08:47:46.736589+01	2026-11-19 08:47:46.739548+01		Init		Using extra environment variables during compile \n	0	c162b0d8-f4b1-4412-a5e0-56deb6c32507
0f1aae1e-905a-4d6a-bd39-c07d14c56697	2026-11-19 08:47:46.739813+01	2026-11-19 08:47:46.740322+01		Venv check		Found existing venv\n	0	c162b0d8-f4b1-4412-a5e0-56deb6c32507
48925b6e-e442-42a9-af29-40d835030590	2026-11-19 08:47:47.783066+01	2026-11-19 08:47:47.783446+01		Venv check		Found existing venv\n	0	67c3c66e-dbac-4199-a6cf-8592711cabd4
1572d476-e695-4a49-a81b-e78cb499da20	2026-11-19 08:47:48.816744+01	2026-11-19 08:47:49.142264+01	/tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpgzuw8u_s/server/fe36bec6-932d-4537-b03c-27798f86fb9e/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	dad8bec6-fccc-43ac-a435-aa85c62876aa
ce623d57-99c5-4b2b-8d6e-f6596215842c	2026-11-19 08:47:48.811201+01	2026-11-19 08:47:48.815021+01		Init		Using extra environment variables during compile \n	0	dad8bec6-fccc-43ac-a435-aa85c62876aa
bc4aad56-e7cc-471f-8e61-552d52d1afc1	2026-11-19 08:47:48.815235+01	2026-11-19 08:47:48.815631+01		Venv check		Found existing venv\n	0	dad8bec6-fccc-43ac-a435-aa85c62876aa
3525544b-329b-4660-9281-f7b654e06b0f	2026-11-19 08:48:03.053342+01	2026-11-19 08:48:03.058752+01		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpgzuw8u_s/server/ac629c48-2c92-430b-a856-db13352a697b/compiler and no repository set.\n	1	cb8ef7c6-05e2-4286-bded-f5da07d7ffd9
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	708f4049-2d5f-4998-b03c-0fd50b10e288
4503df51-663b-4ecb-8d50-5bca78087c61	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	b9093b27-4156-4b8d-95db-943c3dca5c91
4503df51-663b-4ecb-8d50-5bca78087c61	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b9093b27-4156-4b8d-95db-943c3dca5c91
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	afbfb107-297a-408b-b091-da8c25c4b3e5
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	35498c2c-ff01-4e33-88fb-55d9f3aadbfc
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	35498c2c-ff01-4e33-88fb-55d9f3aadbfc
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d237a4a4-70d4-4502-be31-b672eede5fa1
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	36ea6cdc-3d35-4718-8cb3-ea582ebae3dc
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	1bccf1b9-5fbd-4381-84e8-d4bf600410ea
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6adb9ba1-b871-4d11-aad8-9f86c002ec6c
fe36bec6-932d-4537-b03c-27798f86fb9e	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	ba366e55-cac5-4945-bd59-bd5ed6d62010
fe36bec6-932d-4537-b03c-27798f86fb9e	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	f3e0578b-e283-4af2-9734-47b881252d29
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a02cef1f-de2b-402f-9670-01d1a1498c74
fe36bec6-932d-4537-b03c-27798f86fb9e	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	69b7da6d-9c1a-475d-b75b-69852576e14b
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	217c9fb4-8667-4366-91ea-1345af7abd28
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	217c9fb4-8667-4366-91ea-1345af7abd28
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
87aabe20-8087-4309-8e2a-4ee7ab8f1cdd	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-11-19 08:48:02.785134+01
abc33fce-a8fe-4925-9259-6328f81c7533	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-11-19 08:48:02.789301+01
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Fail[agent1,key=key2]	2026-11-19 08:48:02.6308+01	\N	2026-11-19 08:48:02.6308+01	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:48:02.616639+01	f	\N	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test]	2026-11-19 08:47:27.508091+01	\N	2026-11-19 08:47:27.508091+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:47:27.454821+01	f	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key11]	2026-11-19 08:48:02.789301+01	\N	2026-11-19 08:48:02.789301+01	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.76949+01	f	abc33fce-a8fe-4925-9259-6328f81c7533	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key1]	2026-11-19 08:48:02.637994+01	2026-11-19 08:48:02.633591+01	2026-11-19 08:48:02.637994+01	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.616639+01	t	\N	\N
4503df51-663b-4ecb-8d50-5bca78087c61	std::AgentConfig[internal,agentname=localhost]	2026-11-19 08:47:44.359459+01	\N	2026-11-19 08:47:44.359459+01	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:47:44.3309+01	f	\N	\N
4503df51-663b-4ecb-8d50-5bca78087c61	fs::File[localhost,path=/tmp/test]	2026-11-19 08:47:44.364163+01	\N	2026-11-19 08:47:44.364163+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:47:44.3309+01	f	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key3]	2026-11-19 08:48:02.643608+01	\N	2026-11-19 08:48:02.643608+01	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-11-19 08:48:02.616639+01	f	\N	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	fs::File[localhost,path=/tmp/test_orphan]	2026-11-19 08:47:46.600915+01	\N	2026-11-19 08:47:46.600915+01	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:47:46.582156+01	f	\N	3
fe36bec6-932d-4537-b03c-27798f86fb9e	test::Resource[agent2,key=key2]	2026-11-19 08:48:02.198241+01	\N	2026-11-19 08:48:02.198241+01	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:48:02.191482+01	f	\N	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	test::Resource[agent3,key=key3]	2026-11-19 08:48:02.19966+01	\N	2026-11-19 08:48:02.19966+01	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-11-19 08:48:02.191482+01	f	\N	7
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-11-19 08:48:02.616639+01	\N	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-11-19 08:48:02.616639+01	\N	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key6]	2026-11-19 08:48:02.641963+01	2026-11-19 08:48:02.638852+01	2026-11-19 08:48:02.641963+01	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.616639+01	t	\N	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key9]	2026-11-19 08:48:02.777792+01	2026-11-19 08:48:02.772577+01	2026-11-19 08:48:02.777792+01	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.76949+01	t	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key7]	2026-11-19 08:48:02.781541+01	2026-11-19 08:48:02.77863+01	2026-11-19 08:48:02.781541+01	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.76949+01	t	\N	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	test::Resource[agent1,key=key10]	2026-11-19 08:48:02.785134+01	\N	2026-11-19 08:48:02.785134+01	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-19 08:48:02.76949+01	f	87aabe20-8087-4309-8e2a-4ee7ab8f1cdd	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	708f4049-2d5f-4998-b03c-0fd50b10e288	\N
4503df51-663b-4ecb-8d50-5bca78087c61	b9093b27-4156-4b8d-95db-943c3dca5c91	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	afbfb107-297a-408b-b091-da8c25c4b3e5	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	35498c2c-ff01-4e33-88fb-55d9f3aadbfc	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	d237a4a4-70d4-4502-be31-b672eede5fa1	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	36ea6cdc-3d35-4718-8cb3-ea582ebae3dc	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	1bccf1b9-5fbd-4381-84e8-d4bf600410ea	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	6adb9ba1-b871-4d11-aad8-9f86c002ec6c	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	ba366e55-cac5-4945-bd59-bd5ed6d62010	set-b
fe36bec6-932d-4537-b03c-27798f86fb9e	f3e0578b-e283-4af2-9734-47b881252d29	set-a
fe36bec6-932d-4537-b03c-27798f86fb9e	a02cef1f-de2b-402f-9670-01d1a1498c74	\N
fe36bec6-932d-4537-b03c-27798f86fb9e	69b7da6d-9c1a-475d-b75b-69852576e14b	set-a
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	08127817-e11c-4ce8-9a94-192eaa6c4b10	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2c143521-218b-4127-82e0-bd5b27e60835	\N
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	217c9fb4-8667-4366-91ea-1345af7abd28	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	1	708f4049-2d5f-4998-b03c-0fd50b10e288
4503df51-663b-4ecb-8d50-5bca78087c61	1	b9093b27-4156-4b8d-95db-943c3dca5c91
fe36bec6-932d-4537-b03c-27798f86fb9e	2	afbfb107-297a-408b-b091-da8c25c4b3e5
fe36bec6-932d-4537-b03c-27798f86fb9e	3	35498c2c-ff01-4e33-88fb-55d9f3aadbfc
fe36bec6-932d-4537-b03c-27798f86fb9e	4	d237a4a4-70d4-4502-be31-b672eede5fa1
fe36bec6-932d-4537-b03c-27798f86fb9e	5	36ea6cdc-3d35-4718-8cb3-ea582ebae3dc
fe36bec6-932d-4537-b03c-27798f86fb9e	6	1bccf1b9-5fbd-4381-84e8-d4bf600410ea
fe36bec6-932d-4537-b03c-27798f86fb9e	7	6adb9ba1-b871-4d11-aad8-9f86c002ec6c
fe36bec6-932d-4537-b03c-27798f86fb9e	7	ba366e55-cac5-4945-bd59-bd5ed6d62010
fe36bec6-932d-4537-b03c-27798f86fb9e	7	f3e0578b-e283-4af2-9734-47b881252d29
fe36bec6-932d-4537-b03c-27798f86fb9e	8	a02cef1f-de2b-402f-9670-01d1a1498c74
fe36bec6-932d-4537-b03c-27798f86fb9e	8	69b7da6d-9c1a-475d-b75b-69852576e14b
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	08127817-e11c-4ce8-9a94-192eaa6c4b10
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	2c143521-218b-4127-82e0-bd5b27e60835
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	3	217c9fb4-8667-4366-91ea-1345af7abd28
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
65880d9a-b64a-49ae-833c-6203b9769573	store	2026-11-19 08:47:27.315371+01	2026-11-19 08:47:27.321946+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-19T08:47:27.321956+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	1	{"fs::File[localhost,path=/tmp/test],v=1"}
3a90bf16-e0b1-4ff9-b852-d4d3af53523b	deploy	2026-11-19 08:47:27.479683+01	2026-11-19 08:47:27.508091+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:47:27.506448+01:00\\"}"}	unavailable	\N	nochange	fe36bec6-932d-4537-b03c-27798f86fb9e	1	{"fs::File[localhost,path=/tmp/test],v=1"}
c69394ce-d14d-458f-9153-2d003b1363f7	store	2026-11-19 08:47:44.222687+01	2026-11-19 08:47:44.225354+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-19T08:47:44.225363+01:00\\"}"}	\N	\N	\N	4503df51-663b-4ecb-8d50-5bca78087c61	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
10520eaa-3883-4d7c-a07a-a51fb464e63e	deploy	2026-11-19 08:47:44.350547+01	2026-11-19 08:47:44.359459+01	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:47:44.358947+01:00\\"}"}	unavailable	\N	nochange	4503df51-663b-4ecb-8d50-5bca78087c61	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
1826171b-08fc-4ae0-a8ea-a0c2dffccd91	deploy	2026-11-19 08:47:44.363077+01	2026-11-19 08:47:44.364163+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:47:44.363755+01:00\\"}"}	unavailable	\N	nochange	4503df51-663b-4ecb-8d50-5bca78087c61	1	{"fs::File[localhost,path=/tmp/test],v=1"}
37a88758-adae-44a1-9e86-85d68169d4cd	store	2026-11-19 08:47:45.383826+01	2026-11-19 08:47:45.38575+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-19T08:47:45.385759+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	2	{"fs::File[localhost,path=/tmp/test],v=2"}
b016cbdc-cacd-4e83-9cfc-820ea98511bb	store	2026-11-19 08:47:46.45986+01	2026-11-19 08:47:46.464924+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-19T08:47:46.464933+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
5c5f86ab-ebba-48c2-8e2b-698e4d6b2717	deploy	2026-11-19 08:47:46.594495+01	2026-11-19 08:47:46.600915+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-11-19T08:47:46.599480+01:00\\"}"}	unavailable	\N	nochange	fe36bec6-932d-4537-b03c-27798f86fb9e	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
a2ff65e2-e042-4ffd-830b-91763967d50a	store	2026-11-19 08:47:47.633562+01	2026-11-19 08:47:47.635591+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-11-19T08:47:47.635600+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	4	{"fs::File[localhost,path=/tmp/test],v=4"}
ebb995e7-2c27-41da-bf1c-f0c455557397	store	2026-11-19 08:47:48.660935+01	2026-11-19 08:47:48.662838+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-11-19T08:47:48.662846+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	5	{"fs::File[localhost,path=/tmp/test],v=5"}
25693fd1-2ac7-4f79-89ce-a2b2506fe8b1	store	2026-11-19 08:48:02.00302+01	2026-11-19 08:48:02.004836+01	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-11-19T08:48:02.004844+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	6	{"fs::File[localhost,path=/tmp/test],v=6"}
8e22ee81-a864-4efa-8033-945ecd159557	store	2026-11-19 08:48:02.140382+01	2026-11-19 08:48:02.169853+01	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-11-19T08:48:02.169864+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7"}
932850e7-2783-4aab-a8d0-e440cd1defa2	deploy	2026-11-19 08:48:02.196267+01	2026-11-19 08:48:02.198241+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.197688+01:00\\"}"}	unavailable	\N	nochange	fe36bec6-932d-4537-b03c-27798f86fb9e	7	{"test::Resource[agent2,key=key2],v=7"}
96fa46d8-6f1f-4384-a847-79214df4cb97	deploy	2026-11-19 08:48:02.198297+01	2026-11-19 08:48:02.19966+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.199205+01:00\\"}"}	unavailable	\N	nochange	fe36bec6-932d-4537-b03c-27798f86fb9e	7	{"test::Resource[agent3,key=key3],v=7"}
1f0e905d-e102-4663-aa03-4efae707e10d	store	2026-11-19 08:48:02.328985+01	2026-11-19 08:48:02.343538+01	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-11-19T08:48:02.343567+01:00\\"}"}	\N	\N	\N	fe36bec6-932d-4537-b03c-27798f86fb9e	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
f410181d-8f03-4479-ae71-36fea9cc9c83	store	2026-11-19 08:48:02.60784+01	2026-11-19 08:48:02.614768+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-19T08:48:02.614775+01:00\\"}"}	\N	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key3],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key4],v=1"}
c5150901-2290-482f-a7a1-aea46ed991af	deploy	2026-11-19 08:48:02.621581+01	2026-11-19 08:48:02.6308+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: c9156ff9-342f-4b67-bad8-89ae59e60964).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"c9156ff9-342f-4b67-bad8-89ae59e60964\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.629481+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2656, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.630266+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: c9156ff9-342f-4b67-bad8-89ae59e60964) - duration: 0.0012 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0012311935424804688, \\"deploy_id\\": \\"c9156ff9-342f-4b67-bad8-89ae59e60964\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.630766+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Fail[agent1,key=key2],v=1"}
f37f53fb-a3bc-4218-8fc3-7de49b9564da	deploy	2026-11-19 08:48:02.633621+01	2026-11-19 08:48:02.637994+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 53d0dd46-663c-4a8b-83fe-56e3b3c49712).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"53d0dd46-663c-4a8b-83fe-56e3b3c49712\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.634297+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 53d0dd46-663c-4a8b-83fe-56e3b3c49712) - duration: 0.0036 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.003621816635131836, \\"deploy_id\\": \\"53d0dd46-663c-4a8b-83fe-56e3b3c49712\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.637961+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key1],v=1"}
293e0568-4976-459b-8af9-971f38efc268	deploy	2026-11-19 08:48:02.63888+01	2026-11-19 08:48:02.641963+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 5e055b38-86de-49da-a780-d602eee0c004).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"5e055b38-86de-49da-a780-d602eee0c004\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.639529+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 5e055b38-86de-49da-a780-d602eee0c004) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0023674964904785156, \\"deploy_id\\": \\"5e055b38-86de-49da-a780-d602eee0c004\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.641936+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key6],v=1"}
b2e2e363-0ef5-43f9-925f-e13d8eec57c6	deploy	2026-11-19 08:48:02.642731+01	2026-11-19 08:48:02.643608+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 2791f95a-e1f6-4b30-8ee1-63052c3d9096).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"2791f95a-e1f6-4b30-8ee1-63052c3d9096\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.643373+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.643508+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 2791f95a-e1f6-4b30-8ee1-63052c3d9096) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00017881393432617188, \\"deploy_id\\": \\"2791f95a-e1f6-4b30-8ee1-63052c3d9096\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.643586+01:00\\"}"}	skipped	\N	nochange	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key3],v=1"}
53ad85b1-856a-4254-a8ce-65a9da85aa4b	dryrun	2026-11-19 08:48:02.760914+01	2026-11-19 08:48:02.761411+01	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.760967+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00038361549377441406, \\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.761397+01:00\\"}"}	dry	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Fail[agent1,key=key2],v=1"}
0e566349-171b-4d64-9e9c-ad3b2b3121bc	dryrun	2026-11-19 08:48:02.76383+01	2026-11-19 08:48:02.764086+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.763873+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00016355514526367188, \\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.764074+01:00\\"}"}	dry	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key1],v=1"}
fef0931e-cb86-4f5c-881a-7c9920ec2933	dryrun	2026-11-19 08:48:02.765247+01	2026-11-19 08:48:02.76553+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.765293+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0001888275146484375, \\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.765517+01:00\\"}"}	dry	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key3],v=1"}
dbfc8308-100f-4d24-a690-5b8e87c23e1c	dryrun	2026-11-19 08:48:02.766916+01	2026-11-19 08:48:02.767203+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.766959+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00019621849060058594, \\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.767190+01:00\\"}"}	dry	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key5],v=1"}
bb9d5331-78cd-4ef6-8479-063aa8578cff	dryrun	2026-11-19 08:48:02.769126+01	2026-11-19 08:48:02.769361+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.769173+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: c1f44931-4f10-4451-b95e-c7c5acb07ec2 - duration 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00013947486877441406, \\"dry_run_id\\": \\"c1f44931-4f10-4451-b95e-c7c5acb07ec2\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.769349+01:00\\"}"}	dry	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1	{"test::Resource[agent1,key=key6],v=1"}
5ed76036-04d1-45a8-a8e2-d54997893358	store	2026-11-19 08:48:02.914421+01	2026-11-19 08:48:02.91632+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-19T08:48:02.916327+01:00\\"}"}	\N	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	3	{"test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key8],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key7],v=3"}
439145c9-0e2e-4f3f-b3df-6b94ed7367e7	store	2026-11-19 08:48:02.763911+01	2026-11-19 08:48:02.766532+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-19T08:48:02.766540+01:00\\"}"}	\N	\N	\N	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	{"test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key9],v=2"}
5bd19290-8246-4ce6-b43b-79d45794358f	deploy	2026-11-19 08:48:02.772611+01	2026-11-19 08:48:02.777792+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 9cd37ddd-2dbe-44c5-99d2-c5b884fd2b2f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"9cd37ddd-2dbe-44c5-99d2-c5b884fd2b2f\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.774167+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 9cd37ddd-2dbe-44c5-99d2-c5b884fd2b2f) - duration: 0.0036 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0035505294799804688, \\"deploy_id\\": \\"9cd37ddd-2dbe-44c5-99d2-c5b884fd2b2f\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.777760+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	{"test::Resource[agent1,key=key9],v=2"}
1de06f15-9a89-418c-a438-c966925d3737	deploy	2026-11-19 08:48:02.778658+01	2026-11-19 08:48:02.781541+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 0597a9da-9d2a-42b3-af2d-c67f18fbf8c8).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"0597a9da-9d2a-42b3-af2d-c67f18fbf8c8\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.779299+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 0597a9da-9d2a-42b3-af2d-c67f18fbf8c8) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0021746158599853516, \\"deploy_id\\": \\"0597a9da-9d2a-42b3-af2d-c67f18fbf8c8\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.781513+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	{"test::Resource[agent1,key=key7],v=2"}
77048db9-41a2-405d-9e7c-13376a0e759b	deploy	2026-11-19 08:48:02.78231+01	2026-11-19 08:48:02.785134+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1d6de589-c21c-481f-a24c-4fee9d4d5a03).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"1d6de589-c21c-481f-a24c-4fee9d4d5a03\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.782861+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.783045+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 1d6de589-c21c-481f-a24c-4fee9d4d5a03) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0022068023681640625, \\"deploy_id\\": \\"1d6de589-c21c-481f-a24c-4fee9d4d5a03\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.785107+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	{"test::Resource[agent1,key=key10],v=2"}
22be5141-817e-4408-a442-4927a58e8c74	deploy	2026-11-19 08:48:02.786391+01	2026-11-19 08:48:02.789301+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 25593f06-41a5-4e95-a616-cfd07605cbc3).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"25593f06-41a5-4e95-a616-cfd07605cbc3\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.786938+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.787104+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 25593f06-41a5-4e95-a616-cfd07605cbc3) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.002295970916748047, \\"deploy_id\\": \\"25593f06-41a5-4e95-a616-cfd07605cbc3\\"}, \\"timestamp\\": \\"2026-11-19T08:48:02.789273+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2	{"test::Resource[agent1,key=key11],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
fe36bec6-932d-4537-b03c-27798f86fb9e	65880d9a-b64a-49ae-833c-6203b9769573	fs::File[localhost,path=/tmp/test]	1
fe36bec6-932d-4537-b03c-27798f86fb9e	3a90bf16-e0b1-4ff9-b852-d4d3af53523b	fs::File[localhost,path=/tmp/test]	1
4503df51-663b-4ecb-8d50-5bca78087c61	c69394ce-d14d-458f-9153-2d003b1363f7	fs::File[localhost,path=/tmp/test]	1
4503df51-663b-4ecb-8d50-5bca78087c61	c69394ce-d14d-458f-9153-2d003b1363f7	std::AgentConfig[internal,agentname=localhost]	1
4503df51-663b-4ecb-8d50-5bca78087c61	10520eaa-3883-4d7c-a07a-a51fb464e63e	std::AgentConfig[internal,agentname=localhost]	1
4503df51-663b-4ecb-8d50-5bca78087c61	1826171b-08fc-4ae0-a8ea-a0c2dffccd91	fs::File[localhost,path=/tmp/test]	1
fe36bec6-932d-4537-b03c-27798f86fb9e	37a88758-adae-44a1-9e86-85d68169d4cd	fs::File[localhost,path=/tmp/test]	2
fe36bec6-932d-4537-b03c-27798f86fb9e	b016cbdc-cacd-4e83-9cfc-820ea98511bb	fs::File[localhost,path=/tmp/test]	3
fe36bec6-932d-4537-b03c-27798f86fb9e	b016cbdc-cacd-4e83-9cfc-820ea98511bb	fs::File[localhost,path=/tmp/test_orphan]	3
fe36bec6-932d-4537-b03c-27798f86fb9e	5c5f86ab-ebba-48c2-8e2b-698e4d6b2717	fs::File[localhost,path=/tmp/test_orphan]	3
fe36bec6-932d-4537-b03c-27798f86fb9e	a2ff65e2-e042-4ffd-830b-91763967d50a	fs::File[localhost,path=/tmp/test]	4
fe36bec6-932d-4537-b03c-27798f86fb9e	ebb995e7-2c27-41da-bf1c-f0c455557397	fs::File[localhost,path=/tmp/test]	5
fe36bec6-932d-4537-b03c-27798f86fb9e	25693fd1-2ac7-4f79-89ce-a2b2506fe8b1	fs::File[localhost,path=/tmp/test]	6
fe36bec6-932d-4537-b03c-27798f86fb9e	8e22ee81-a864-4efa-8033-945ecd159557	fs::File[localhost,path=/tmp/test]	7
fe36bec6-932d-4537-b03c-27798f86fb9e	8e22ee81-a864-4efa-8033-945ecd159557	test::Resource[agent2,key=key2]	7
fe36bec6-932d-4537-b03c-27798f86fb9e	8e22ee81-a864-4efa-8033-945ecd159557	test::Resource[agent3,key=key3]	7
fe36bec6-932d-4537-b03c-27798f86fb9e	932850e7-2783-4aab-a8d0-e440cd1defa2	test::Resource[agent2,key=key2]	7
fe36bec6-932d-4537-b03c-27798f86fb9e	96fa46d8-6f1f-4384-a847-79214df4cb97	test::Resource[agent3,key=key3]	7
fe36bec6-932d-4537-b03c-27798f86fb9e	1f0e905d-e102-4663-aa03-4efae707e10d	test::Resource[agent2,key=key2]	8
fe36bec6-932d-4537-b03c-27798f86fb9e	1f0e905d-e102-4663-aa03-4efae707e10d	fs::File[localhost,path=/tmp/test]	8
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Resource[agent1,key=key3]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Fail[agent1,key=key2]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Resource[agent1,key=key1]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Resource[agent1,key=key6]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Resource[agent1,key=key5]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f410181d-8f03-4479-ae71-36fea9cc9c83	test::Resource[agent1,key=key4]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	c5150901-2290-482f-a7a1-aea46ed991af	test::Fail[agent1,key=key2]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	f37f53fb-a3bc-4218-8fc3-7de49b9564da	test::Resource[agent1,key=key1]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	293e0568-4976-459b-8af9-971f38efc268	test::Resource[agent1,key=key6]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	b2e2e363-0ef5-43f9-925f-e13d8eec57c6	test::Resource[agent1,key=key3]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	53ad85b1-856a-4254-a8ce-65a9da85aa4b	test::Fail[agent1,key=key2]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	0e566349-171b-4d64-9e9c-ad3b2b3121bc	test::Resource[agent1,key=key1]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	fef0931e-cb86-4f5c-881a-7c9920ec2933	test::Resource[agent1,key=key3]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key10]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key1]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key3]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key5]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Fail[agent1,key=key2]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key7]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key11]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key4]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	439145c9-0e2e-4f3f-b3df-6b94ed7367e7	test::Resource[agent1,key=key9]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	dbfc8308-100f-4d24-a690-5b8e87c23e1c	test::Resource[agent1,key=key5]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	bb9d5331-78cd-4ef6-8479-063aa8578cff	test::Resource[agent1,key=key6]	1
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5bd19290-8246-4ce6-b43b-79d45794358f	test::Resource[agent1,key=key9]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	1de06f15-9a89-418c-a438-c966925d3737	test::Resource[agent1,key=key7]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	77048db9-41a2-405d-9e7c-13376a0e759b	test::Resource[agent1,key=key10]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	22be5141-817e-4408-a442-4927a58e8c74	test::Resource[agent1,key=key11]	2
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key4]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key5]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key3]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key1]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key8]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Fail[agent1,key=key2]	3
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	5ed76036-04d1-45a8-a8e2-d54997893358	test::Resource[agent1,key=key7]	3
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
4503df51-663b-4ecb-8d50-5bca78087c61	1
fe36bec6-932d-4537-b03c-27798f86fb9e	8
b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	fe36bec6-932d-4537-b03c-27798f86fb9e	2026-11-19 08:47:10.814955+01	\N	23405cd2-9e8f-4981-8b35-bce3961c6a51
hugo-Latitude-5421	4503df51-663b-4ecb-8d50-5bca78087c61	2026-11-19 08:47:10.933861+01	\N	197d69db-bdd8-453b-966b-dd08fb9d0986
hugo-Latitude-5421	b5def7cb-0f4a-4eb7-a184-1f958cf28fae	2026-11-19 08:48:02.468123+01	2026-11-19 08:48:02.910647+01	d868b49d-ad75-449a-913f-7d05f959bdc1
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610161,202610280,202611170,202611190}
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
-- Name: dryrun_resource dryrun_resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun_resource
    ADD CONSTRAINT dryrun_resource_pkey PRIMARY KEY (dryrun_id, resource_id);


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
-- Name: dryrun_resource dryrun_resource_dryrun_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dryrun_resource
    ADD CONSTRAINT dryrun_resource_dryrun_id_fkey FOREIGN KEY (dryrun_id) REFERENCES public.dryrun(id) ON DELETE CASCADE;


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

