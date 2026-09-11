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
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	$__scheduler	f	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	$__scheduler	f	\N
5b69215c-8989-446e-9d6a-e0b20f8619d4	$__scheduler	f	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	localhost	f	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	internal	f	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	localhost	f	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	internal	f	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	agent3	f	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	agent2	f	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	agent1	t	t
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	$__scheduler	t	t
167a2583-2430-4978-a23c-ed7055989804	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
1	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
1	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
1	internal	std	813f0711-6e78-43fd-ae4b-7911fd102d24
1	localhost	fs	813f0711-6e78-43fd-ae4b-7911fd102d24
2	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
2	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
2	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
3	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
3	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
3	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
4	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
4	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
4	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
5	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
5	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
5	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
6	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
6	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
6	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
7	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
7	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
7	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
8	localhost	fs	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
8	internal	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
8	localhost	std	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
82fd4529-d037-4615-9c0f-0b032a96800f	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:08.328259+02	2026-09-11 15:16:23.560536+02	2026-09-11 15:16:08.320773+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	9b11d3f3-9310-4b72-8b4f-521c6c703796	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a97a6257-8165-4ace-8d91-eaeba8a5c947	813f0711-6e78-43fd-ae4b-7911fd102d24	2026-09-11 15:16:23.85061+02	2026-09-11 15:16:37.336575+02	2026-09-11 15:16:23.815761+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	894416da-42e3-47e9-b958-e78c3adde020	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
3218fdc0-809f-4a96-a77e-2b965dbf2ba2	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:37.517855+02	2026-09-11 15:16:38.418986+02	2026-09-11 15:16:37.514258+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	768c23e3-ac16-4f2c-a8b7-aa1b6591bec6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
5eeec5be-0297-4c00-8eea-d7304aeb5a78	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:38.523065+02	2026-09-11 15:16:39.495282+02	2026-09-11 15:16:38.462457+02	{}	{"add_one_resource": "true"}	t	f	t	3	63595804-5aa6-4c18-a73b-fa5b9d3e2888	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
3510d150-28d6-40aa-a9ac-91d3de8dd3f2	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:39.67252+02	2026-09-11 15:16:40.628677+02	2026-09-11 15:16:39.658636+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	86e346be-7b86-4e87-947a-ef08761f4a00	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
fa6b62a6-9586-4174-b14c-69bc5a8cb6e9	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:40.831499+02	2026-09-11 15:16:41.748382+02	2026-09-11 15:16:40.828503+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	7b597c36-479c-4468-be4d-71e555c2f0b8	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bc248390-0294-47d8-a5e6-13fed241b324	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:41.852909+02	2026-09-11 15:16:54.938617+02	2026-09-11 15:16:41.788082+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	0ea019b8-eb6b-412e-b203-57ab21d0e086	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
21007b2c-8163-4695-8e3b-c6e300011f60	167a2583-2430-4978-a23c-ed7055989804	2026-09-11 15:16:55.81957+02	2026-09-11 15:16:55.826444+02	2026-09-11 15:16:55.806519+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	5b1cfd32-56b3-4c4e-b259-82bbf306cd2b	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:23.540747+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:55.152317+02	t	\N	3	{}	{}	7	t	\N	\N
1	813f0711-6e78-43fd-ae4b-7911fd102d24	2026-09-11 15:16:37.318286+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:38.405438+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:39.48611+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:40.619053+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:41.739217+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:54.929979+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2026-09-11 15:16:55.354877+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:54.979846+02	t	\N	4	{}	{}	6	t	\N	\N
2	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2026-09-11 15:16:55.525626+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2026-09-11 15:16:55.684272+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	fs	1.2.0
813f0711-6e78-43fd-ae4b-7911fd102d24	1	std	7.0.0
813f0711-6e78-43fd-ae4b-7911fd102d24	1	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	4	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	4	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	5	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	5	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	6	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	6	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	std	8.7.4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8	fs	1.2.0
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8	std	8.7.4
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	discovery::Discovered[myagent,name=discovered]	{}	2026-09-11 15:16:55.687894+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-09-11 15:16:55.687915+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
6b7912e3-d74a-46b4-91db-d5d86aedb14a	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	2026-09-11 15:16:55.492869+02	6	0	{"3f318241-5350-56da-bd4c-c1087a155a3b": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "87032c8e-5bef-5e0e-89b5-935ad1ee9d97": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "8969b16f-07b3-5acb-8074-67873d0a99c8": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "aa39539d-7327-5278-97ab-e7dd61e65ed8": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "ede8c6d8-3552-56d1-9c8f-f59785adf657": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "f8a258d7-0bf2-53c1-8898-330f11c07a5b": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}}
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
167a2583-2430-4978-a23c-ed7055989804	dev-4	b5bd77b5-12de-423c-b80c-e86245d27ceb			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	dev-1	b5bd77b5-12de-423c-b80c-e86245d27ceb			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
813f0711-6e78-43fd-ae4b-7911fd102d24	dev-1-twin	b5bd77b5-12de-423c-b80c-e86245d27ceb			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
5b69215c-8989-446e-9d6a-e0b20f8619d4	dev-2	b5bd77b5-12de-423c-b80c-e86245d27ceb			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	dev-3	b5bd77b5-12de-423c-b80c-e86245d27ceb			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.4	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	\N	\N	\N	package
fs	1.2.0	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	\N	\N	\N	package
std	7.0.0	813f0711-6e78-43fd-ae4b-7911fd102d24	\N	\N	\N	package
fs	1.2.0	813f0711-6e78-43fd-ae4b-7911fd102d24	\N	\N	\N	package
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
61b32c4f-4786-4e4c-9109-2e36887ab113	167a2583-2430-4978-a23c-ed7055989804	2026-09-11 15:16:55.832896+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/21007b2c-8163-4695-8e3b-c6e300011f60	f	f	21007b2c-8163-4695-8e3b-c6e300011f60
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
1b8c697b-f338-4978-9450-de794f653059	fact1	value1	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::testing::NullResource[localhost,name=test1]	fact	2026-09-11 15:16:40.810585+02	{}	f
3334c79d-660e-48dc-891e-273b90c1f3b6	fact2	value2	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::testing::NullResource[localhost,name=test2]	fact	2026-09-11 15:16:40.817433+02	{}	t
a4e4f803-7d28-45cf-8b24-ad7ef6f8c830	fact3	value3	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::testing::NullResource[localhost,name=test3]	fact	2026-09-11 15:16:40.819715+02	{}	t
2c33e794-8ed1-4bca-bc5e-f6b637c02d8d	parameter1	value1	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3		fact	2026-09-11 15:16:40.821921+02	{}	f
d086d71e-f5d4-476d-8fae-333c2da2de47	parameter2	value2	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3		fact	2026-09-11 15:16:40.824111+02	{}	f
58893090-6cc4-4424-a23b-abdf96433e3f	parameter3	value3	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3		fact	2026-09-11 15:16:40.826351+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
b5bd77b5-12de-423c-b80c-e86245d27ceb	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
85dfc452-3bde-48a4-8cdb-7a554ddc3a00	2026-09-11 15:16:08.328617+02	2026-09-11 15:16:08.331028+02		Init		Using extra environment variables during compile \n	0	82fd4529-d037-4615-9c0f-0b032a96800f
b738757c-54ad-4403-9843-f8bed3d9c20b	2026-09-11 15:16:08.331321+02	2026-09-11 15:16:08.34016+02		Venv check		Creating new venv at /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env-py3.13\n	0	82fd4529-d037-4615-9c0f-0b032a96800f
874fd032-31c5-4e0e-98dc-3dad42a8487c	2026-09-11 15:16:08.341883+02	2026-09-11 15:16:08.657266+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	82fd4529-d037-4615-9c0f-0b032a96800f
659ddd4b-a7dc-400a-8503-46bb7371501a	2026-09-11 15:16:41.872739+02	2026-09-11 15:16:42.231727+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	bc248390-0294-47d8-a5e6-13fed241b324
181f646a-3f42-449b-8459-4b90d54f3866	2026-09-11 15:16:08.658251+02	2026-09-11 15:16:22.630067+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp0tdorzim:\n                                 Pip command: /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp0tdorzim inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, build, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	82fd4529-d037-4615-9c0f-0b032a96800f
c3ce4c79-c001-4982-8ddc-95173c320a77	2026-09-11 15:16:41.854859+02	2026-09-11 15:16:41.865041+02		Init		Using extra environment variables during compile \n	0	bc248390-0294-47d8-a5e6-13fed241b324
fe1e7d4d-4d7b-4ed9-8877-4d5a483bfa8b	2026-09-11 15:16:41.866269+02	2026-09-11 15:16:41.868298+02		Venv check		Found existing venv\n	0	bc248390-0294-47d8-a5e6-13fed241b324
9260bd1e-8ff9-44fb-a943-74af171d672d	2026-09-11 15:16:37.518208+02	2026-09-11 15:16:37.520184+02		Init		Using extra environment variables during compile \n	0	3218fdc0-809f-4a96-a77e-2b965dbf2ba2
38075ac6-262b-482c-a03b-86852f6d0193	2026-09-11 15:16:22.630832+02	2026-09-11 15:16:23.560027+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpp7pk83um --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.024 seconds\ncompiler       DEBUG   The entire export command took 0.068 seconds\n	0	82fd4529-d037-4615-9c0f-0b032a96800f
3d5d6fbe-bb43-4246-afdd-ef220ea80b0b	2026-09-11 15:16:23.852954+02	2026-09-11 15:16:23.864113+02		Init		Using extra environment variables during compile \n	0	a97a6257-8165-4ace-8d91-eaeba8a5c947
1606cf79-1480-4751-b8d7-e5771fe98e65	2026-09-11 15:16:37.520381+02	2026-09-11 15:16:37.52079+02		Venv check		Found existing venv\n	0	3218fdc0-809f-4a96-a77e-2b965dbf2ba2
de731308-2f14-4148-bdf9-048754b85739	2026-09-11 15:16:23.865643+02	2026-09-11 15:16:23.891459+02		Venv check		Creating new venv at /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env-py3.13\n	0	a97a6257-8165-4ace-8d91-eaeba8a5c947
20d38fcf-b299-4fda-9f9e-a76787c087ee	2026-09-11 15:16:23.896611+02	2026-09-11 15:16:24.222037+02	/tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 18.3.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	a97a6257-8165-4ace-8d91-eaeba8a5c947
74780a37-78a6-44f7-a875-0e5189684984	2026-09-11 15:16:24.222743+02	2026-09-11 15:16:36.403665+02	/tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp2m4u30y1:\n                                 Pip command: /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp2m4u30y1 inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Collecting build~=1.0 (from inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached build-1.6.1-py3-none-any.whl (31 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.0.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.53-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify, mitogen, build, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 8.0.4\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: build\ninmanta.pip              DEBUG   Found existing installation: build 1.6.0\ninmanta.pip              DEBUG   Not uninstalling build at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'build'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.4\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages, outside environment /tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed build-1.6.1 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.53 python-slugify-9.0.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.4\n	0	a97a6257-8165-4ace-8d91-eaeba8a5c947
349f8ced-1cd9-42d6-93e4-d37e67f9463f	2026-09-11 15:16:36.40446+02	2026-09-11 15:16:37.336132+02	/tmp/tmp6nc73c7_/server/813f0711-6e78-43fd-ae4b-7911fd102d24/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 813f0711-6e78-43fd-ae4b-7911fd102d24 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpd0318v93 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.020 seconds\ncompiler       DEBUG   The entire export command took 0.061 seconds\n	0	a97a6257-8165-4ace-8d91-eaeba8a5c947
39b3f141-12f6-4c6e-8069-248361a388c3	2026-09-11 15:16:37.520965+02	2026-09-11 15:16:38.418391+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpsp1cmqte --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.057 seconds\n	0	3218fdc0-809f-4a96-a77e-2b965dbf2ba2
98e63f50-d3e4-4ea8-995c-576a059fc992	2026-09-11 15:16:38.524846+02	2026-09-11 15:16:38.534683+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	5eeec5be-0297-4c00-8eea-d7304aeb5a78
11a5e2de-a0f0-4555-8bba-e66cf8eb0383	2026-09-11 15:16:38.535821+02	2026-09-11 15:16:38.537828+02		Venv check		Found existing venv\n	0	5eeec5be-0297-4c00-8eea-d7304aeb5a78
dca5b15d-88f7-4c69-b41d-c039f98acbd5	2026-09-11 15:16:38.538691+02	2026-09-11 15:16:39.494706+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpnhm1xspu --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	5eeec5be-0297-4c00-8eea-d7304aeb5a78
73fe7b9a-626f-40f2-8d12-4f65f4a7933b	2026-09-11 15:16:39.674972+02	2026-09-11 15:16:39.677882+02		Init		Using extra environment variables during compile \n	0	3510d150-28d6-40aa-a9ac-91d3de8dd3f2
7b9dc6f4-d5bb-444a-915c-3edc4d406e4d	2026-09-11 15:16:39.678175+02	2026-09-11 15:16:39.678654+02		Venv check		Found existing venv\n	0	3510d150-28d6-40aa-a9ac-91d3de8dd3f2
82456687-18ad-4ca8-832c-fd1f2c3aff7c	2026-09-11 15:16:40.834785+02	2026-09-11 15:16:40.83525+02		Venv check		Found existing venv\n	0	fa6b62a6-9586-4174-b14c-69bc5a8cb6e9
50d5251f-4381-4f53-b6c9-5f20f1dd72a1	2026-09-11 15:16:39.678839+02	2026-09-11 15:16:40.628291+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpuhxnubd7 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.054 seconds\n	0	3510d150-28d6-40aa-a9ac-91d3de8dd3f2
4cbd6db1-e952-4ac8-8f6b-276ec1552337	2026-09-11 15:16:40.832341+02	2026-09-11 15:16:40.83449+02		Init		Using extra environment variables during compile \n	0	fa6b62a6-9586-4174-b14c-69bc5a8cb6e9
987ae8d0-5d0b-4fef-a522-5d834f01d8f7	2026-09-11 15:16:40.835428+02	2026-09-11 15:16:41.747809+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp4yv8rn6d --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	fa6b62a6-9586-4174-b14c-69bc5a8cb6e9
bd922c50-1b85-4b79-8e5b-993eb1e531b3	2026-09-11 15:16:42.232451+02	2026-09-11 15:16:54.030072+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.4\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpt4ojwv98:\n                                 Pip command: /tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpt4ojwv98 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==18.3.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.13/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (8.7.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.13/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==18.3.0.dev0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (18.3.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.31.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in ./.env/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (50.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.13.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (6.5.8)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.0.52)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.3,>=3.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (3.2.12)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (1.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from inmanta-core==18.3.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from build~=1.0->inmanta-core==18.3.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cryptography<51,>=36->inmanta-core==18.3.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from email-validator<3,>=1->inmanta-core==18.3.0.dev0) (3.19)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from jinja2~=3.0->inmanta-core==18.3.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.46.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (2.46.5)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==18.3.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-dateutil~=2.0->inmanta-core==18.3.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from SQLAlchemy~=2.0->inmanta-core==18.3.0.dev0) (3.5.5)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.327.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from typing_inspect~=0.9->inmanta-core==18.3.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.13/site-packages (from inmanta-module-mitogen) (0.3.53)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==18.3.0.dev0) (3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (3.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==18.3.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2026.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from requests[use_chardet_on_py3]->inmanta-core==18.3.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core313/lib/python3.13/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==18.3.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	bc248390-0294-47d8-a5e6-13fed241b324
558f2097-2a8d-413a-916b-82d7584b9dec	2026-09-11 15:16:54.030721+02	2026-09-11 15:16:54.938172+02	/tmp/tmp6nc73c7_/server/d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3 --server_address localhost --server_port 39023 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmplh2r6ocb --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.4\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39023/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39023/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	bc248390-0294-47d8-a5e6-13fed241b324
f18261db-5ee3-4a05-9814-5db61df329d5	2026-09-11 15:16:55.820909+02	2026-09-11 15:16:55.825551+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp6nc73c7_/server/167a2583-2430-4978-a23c-ed7055989804/compiler and no repository set.\n	1	21007b2c-8163-4695-8e3b-c6e300011f60
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	b0723ae0-a472-4a07-9914-86943aaf9b85
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b0723ae0-a472-4a07-9914-86943aaf9b85
813f0711-6e78-43fd-ae4b-7911fd102d24	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	19f1d230-c97a-438c-82b9-b2ce1504d338
813f0711-6e78-43fd-ae4b-7911fd102d24	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	19f1d230-c97a-438c-82b9-b2ce1504d338
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	03bba7cc-2809-4316-8387-a71f90727f2b
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	03bba7cc-2809-4316-8387-a71f90727f2b
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	3a302d23-59c9-41f1-bb0a-9f494f1f5024
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	3a302d23-59c9-41f1-bb0a-9f494f1f5024
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3a302d23-59c9-41f1-bb0a-9f494f1f5024
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	3806c7e5-fabf-4026-a65f-faa422093ed5
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3806c7e5-fabf-4026-a65f-faa422093ed5
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	0de08727-fe10-4427-a0dd-fc90b4d06ad8
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0de08727-fe10-4427-a0dd-fc90b4d06ad8
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	741664de-be77-435e-b8a9-d2fd9e2895b4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	741664de-be77-435e-b8a9-d2fd9e2895b4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	69c4c639-a2d6-4640-9423-666ab996efb9
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	69c4c639-a2d6-4640-9423-666ab996efb9
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	e243fcfc-c9fc-4e50-9126-9d0298ba7b39
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	ceea1564-8268-414b-b721-29adf373b054
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "report_only": false, "receive_events": true, "purge_on_delete": false}	b8f697829071c376b6c9e448e5bd267d	std::AgentConfig	localhost	f	e9c375be-b139-455b-94b4-eef58a8759d2
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e9c375be-b139-455b-94b4-eef58a8759d2
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	7c9d5ccb-2153-4dad-b037-db8691d009c8
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	a7da71ff-8af5-4ced-aae4-d5b909651572
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	a7da71ff-8af5-4ced-aae4-d5b909651572
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
88563c5c-1370-4597-97ce-bafa37251ba1	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-09-11 15:16:55.548305+02
4bcda39f-e1c3-482b-a93b-1a2a7237936f	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-09-11 15:16:55.553299+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key10]	2026-09-11 15:16:55.548305+02	\N	2026-09-11 15:16:55.548305+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.53303+02	f	88563c5c-1370-4597-97ce-bafa37251ba1	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	std::AgentConfig[internal,agentname=localhost]	2026-09-11 15:16:23.683448+02	\N	2026-09-11 15:16:23.683448+02	b8f697829071c376b6c9e448e5bd267d	1	unavailable	std::AgentConfig	internal	localhost	b8f697829071c376b6c9e448e5bd267d	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:23.6722+02	f	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-09-11 15:16:55.358606+02	\N	\N	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test]	2026-09-11 15:16:23.689089+02	\N	2026-09-11 15:16:23.689089+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:23.6722+02	f	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key11]	2026-09-11 15:16:55.553299+02	\N	2026-09-11 15:16:55.553299+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.53303+02	f	4bcda39f-e1c3-482b-a93b-1a2a7237936f	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key1]	2026-09-11 15:16:55.37084+02	2026-09-11 15:16:55.363124+02	2026-09-11 15:16:55.37084+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.358606+02	t	\N	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	std::AgentConfig[internal,agentname=localhost]	2026-09-11 15:16:37.412947+02	\N	2026-09-11 15:16:37.412947+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:37.399997+02	f	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key7]	2026-09-11 15:16:55.557229+02	2026-09-11 15:16:55.554207+02	2026-09-11 15:16:55.557229+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.53303+02	t	\N	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	fs::File[localhost,path=/tmp/test]	2026-09-11 15:16:37.418423+02	\N	2026-09-11 15:16:37.418423+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:37.399997+02	f	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key9]	2026-09-11 15:16:55.560827+02	2026-09-11 15:16:55.557914+02	2026-09-11 15:16:55.560827+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.53303+02	t	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Fail[agent1,key=key2]	2026-09-11 15:16:55.377626+02	\N	2026-09-11 15:16:55.377626+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:55.358606+02	f	\N	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	fs::File[localhost,path=/tmp/test_orphan]	2026-09-11 15:16:39.532683+02	\N	2026-09-11 15:16:39.532683+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:39.526243+02	f	\N	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key3]	2026-09-11 15:16:55.379471+02	\N	2026-09-11 15:16:55.379471+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-09-11 15:16:55.358606+02	f	\N	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	test::Resource[agent2,key=key2]	2026-09-11 15:16:55.020012+02	\N	2026-09-11 15:16:55.020012+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:55.004444+02	f	\N	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	test::Resource[agent3,key=key3]	2026-09-11 15:16:55.018466+02	\N	2026-09-11 15:16:55.018466+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-09-11 15:16:55.004444+02	f	\N	7
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-09-11 15:16:55.358606+02	\N	\N	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	test::Resource[agent1,key=key6]	2026-09-11 15:16:55.37498+02	2026-09-11 15:16:55.371872+02	2026-09-11 15:16:55.37498+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-09-11 15:16:55.358606+02	t	\N	1
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	b0723ae0-a472-4a07-9914-86943aaf9b85	\N
813f0711-6e78-43fd-ae4b-7911fd102d24	19f1d230-c97a-438c-82b9-b2ce1504d338	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	03bba7cc-2809-4316-8387-a71f90727f2b	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3a302d23-59c9-41f1-bb0a-9f494f1f5024	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3806c7e5-fabf-4026-a65f-faa422093ed5	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	0de08727-fe10-4427-a0dd-fc90b4d06ad8	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	741664de-be77-435e-b8a9-d2fd9e2895b4	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	69c4c639-a2d6-4640-9423-666ab996efb9	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	e243fcfc-c9fc-4e50-9126-9d0298ba7b39	set-b
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	ceea1564-8268-414b-b721-29adf373b054	set-a
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	e9c375be-b139-455b-94b4-eef58a8759d2	\N
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7c9d5ccb-2153-4dad-b037-db8691d009c8	set-a
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	7c160365-3479-4612-9781-cba13af6cf4d	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	171f556f-d5da-47a6-84e2-414888aba094	\N
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	a7da71ff-8af5-4ced-aae4-d5b909651572	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	b0723ae0-a472-4a07-9914-86943aaf9b85
813f0711-6e78-43fd-ae4b-7911fd102d24	1	19f1d230-c97a-438c-82b9-b2ce1504d338
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2	03bba7cc-2809-4316-8387-a71f90727f2b
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3	3a302d23-59c9-41f1-bb0a-9f494f1f5024
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	4	3806c7e5-fabf-4026-a65f-faa422093ed5
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	5	0de08727-fe10-4427-a0dd-fc90b4d06ad8
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	6	741664de-be77-435e-b8a9-d2fd9e2895b4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	69c4c639-a2d6-4640-9423-666ab996efb9
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	e243fcfc-c9fc-4e50-9126-9d0298ba7b39
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	ceea1564-8268-414b-b721-29adf373b054
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8	e9c375be-b139-455b-94b4-eef58a8759d2
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8	7c9d5ccb-2153-4dad-b037-db8691d009c8
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	7c160365-3479-4612-9781-cba13af6cf4d
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	171f556f-d5da-47a6-84e2-414888aba094
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3	a7da71ff-8af5-4ced-aae4-d5b909651572
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
eef68eb1-f104-47f9-b19e-321183e3356b	store	2026-09-11 15:16:23.540689+02	2026-09-11 15:16:23.549423+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T15:16:23.549433+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
c1ba98c8-5bca-46cf-ac90-c0a10b7448f5	deploy	2026-09-11 15:16:23.681507+02	2026-09-11 15:16:23.683448+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:23.682635+02:00\\"}"}	unavailable	\N	nochange	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
5449a91a-bdb9-47ec-8196-8f3495cd369e	deploy	2026-09-11 15:16:23.68793+02	2026-09-11 15:16:23.689089+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:23.688654+02:00\\"}"}	unavailable	\N	nochange	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	1	{"fs::File[localhost,path=/tmp/test],v=1"}
4abe9e1c-b4bb-42f3-a3ac-81dd599bb682	store	2026-09-11 15:16:37.318235+02	2026-09-11 15:16:37.324592+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T15:16:37.324601+02:00\\"}"}	\N	\N	\N	813f0711-6e78-43fd-ae4b-7911fd102d24	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
8558f0ef-d693-401c-9d12-204ab40882a5	deploy	2026-09-11 15:16:37.405558+02	2026-09-11 15:16:37.412947+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:37.412301+02:00\\"}"}	unavailable	\N	nochange	813f0711-6e78-43fd-ae4b-7911fd102d24	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
c78058b2-20c4-4e3e-b8f7-02101e1156f3	deploy	2026-09-11 15:16:37.417233+02	2026-09-11 15:16:37.418423+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:37.417993+02:00\\"}"}	unavailable	\N	nochange	813f0711-6e78-43fd-ae4b-7911fd102d24	1	{"fs::File[localhost,path=/tmp/test],v=1"}
17dec0ac-f0b1-472c-9823-411faf50b999	store	2026-09-11 15:16:38.405378+02	2026-09-11 15:16:38.411442+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-11T15:16:38.411464+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
eb526918-3d8e-4b03-b293-6ffd5eb38b57	store	2026-09-11 15:16:39.486064+02	2026-09-11 15:16:39.488627+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-11T15:16:39.488636+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3	{"std::AgentConfig[internal,agentname=localhost],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
e86ba7c1-0a35-4e2c-9e0f-c606fa5e4d34	deploy	2026-09-11 15:16:39.530689+02	2026-09-11 15:16:39.532683+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-09-11T15:16:39.532202+02:00\\"}"}	unavailable	\N	nochange	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
32fbc0cc-f50d-4ad1-b5ad-ad51fdce728d	store	2026-09-11 15:16:40.619005+02	2026-09-11 15:16:40.621866+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-09-11T15:16:40.621876+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	4	{"std::AgentConfig[internal,agentname=localhost],v=4","fs::File[localhost,path=/tmp/test],v=4"}
3f9f597b-504e-4a1b-9804-afb1f16701c0	store	2026-09-11 15:16:41.739159+02	2026-09-11 15:16:41.741419+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-09-11T15:16:41.741430+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	5	{"std::AgentConfig[internal,agentname=localhost],v=5","fs::File[localhost,path=/tmp/test],v=5"}
e75c64ca-348e-48ed-b370-864280c123f6	store	2026-09-11 15:16:54.929933+02	2026-09-11 15:16:54.931867+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-09-11T15:16:54.931875+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	6	{"std::AgentConfig[internal,agentname=localhost],v=6","fs::File[localhost,path=/tmp/test],v=6"}
d5462da2-2fe5-4da2-88d5-aa4b71b9edba	store	2026-09-11 15:16:54.979743+02	2026-09-11 15:16:54.984137+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-09-11T15:16:54.984144+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	{"std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent3,key=key3],v=7","test::Resource[agent2,key=key2],v=7"}
316a4ebe-5bc7-4bea-9061-4f7917218aae	deploy	2026-09-11 15:16:55.018526+02	2026-09-11 15:16:55.020012+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.019527+02:00\\"}"}	unavailable	\N	nochange	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	{"test::Resource[agent2,key=key2],v=7"}
874f349b-dc8d-44f4-a4f2-dc8fc902622f	deploy	2026-09-11 15:16:55.009809+02	2026-09-11 15:16:55.018466+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.017816+02:00\\"}"}	unavailable	\N	nochange	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	7	{"test::Resource[agent3,key=key3],v=7"}
52b34b9d-99f9-4d91-b204-075bb5b40f2d	store	2026-09-11 15:16:55.151897+02	2026-09-11 15:16:55.180324+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-09-11T15:16:55.180345+02:00\\"}"}	\N	\N	\N	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8","std::AgentConfig[internal,agentname=localhost],v=8"}
3cb1d528-3236-4864-ad4f-cfb2e485ac62	store	2026-09-11 15:16:55.354825+02	2026-09-11 15:16:55.356725+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-09-11T15:16:55.356733+02:00\\"}"}	\N	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key3],v=1"}
9d5a7cde-2fae-41a2-92b8-eb8887b51aae	deploy	2026-09-11 15:16:55.363169+02	2026-09-11 15:16:55.37084+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3e1e8ab1-4ed9-40cd-af16-636ad11f4b4d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"3e1e8ab1-4ed9-40cd-af16-636ad11f4b4d\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.364418+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 3e1e8ab1-4ed9-40cd-af16-636ad11f4b4d) - duration: 0.0063 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.00632786750793457, \\"deploy_id\\": \\"3e1e8ab1-4ed9-40cd-af16-636ad11f4b4d\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.370800+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key1],v=1"}
cba990cb-fa55-41a9-8ac6-a9ff1adbe8be	deploy	2026-09-11 15:16:55.371902+02	2026-09-11 15:16:55.37498+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: a415e440-9e59-4b17-bdba-6373dfa1eb8e).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"a415e440-9e59-4b17-bdba-6373dfa1eb8e\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.372598+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: a415e440-9e59-4b17-bdba-6373dfa1eb8e) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.002305269241333008, \\"deploy_id\\": \\"a415e440-9e59-4b17-bdba-6373dfa1eb8e\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.374945+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key6],v=1"}
302293c6-45b7-4a4f-aa3d-e5a3ffad98d2	deploy	2026-09-11 15:16:55.375768+02	2026-09-11 15:16:55.377626+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 85e159c0-e766-484f-8771-9a8d2d11779d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"85e159c0-e766-484f-8771-9a8d2d11779d\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.376432+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2644, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.377074+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 85e159c0-e766-484f-8771-9a8d2d11779d) - duration: 0.0011 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0011303424835205078, \\"deploy_id\\": \\"85e159c0-e766-484f-8771-9a8d2d11779d\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.377602+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Fail[agent1,key=key2],v=1"}
9f5ca130-1402-4c5b-b92f-58d4c83d2813	deploy	2026-09-11 15:16:55.378558+02	2026-09-11 15:16:55.379471+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1957632b-8a8e-43d1-92b6-d87254b1d18e).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"1957632b-8a8e-43d1-92b6-d87254b1d18e\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.379293+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.379373+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 1957632b-8a8e-43d1-92b6-d87254b1d18e) - duration: 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00012183189392089844, \\"deploy_id\\": \\"1957632b-8a8e-43d1-92b6-d87254b1d18e\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.379448+02:00\\"}"}	skipped	\N	nochange	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key3],v=1"}
dfa74a80-889e-4e26-86f2-5e57a7cb56ba	dryrun	2026-09-11 15:16:55.502269+02	2026-09-11 15:16:55.503447+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.502449+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a - duration 0.0008 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007698535919189453, \\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.503396+02:00\\"}"}	dry	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Fail[agent1,key=key2],v=1"}
379c4a2a-f360-4a22-b471-996ab596c85e	store	2026-09-11 15:16:55.525525+02	2026-09-11 15:16:55.528917+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-09-11T15:16:55.528925+02:00\\"}"}	\N	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	{"test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key4],v=2"}
0089e26c-d7bf-40d2-9ec4-a52db6e28f92	dryrun	2026-09-11 15:16:55.532843+02	2026-09-11 15:16:55.533159+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.532885+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002224445343017578, \\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.533145+02:00\\"}"}	dry	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key6],v=1"}
be2d536b-62a7-4989-b17b-3f9a8539715b	dryrun	2026-09-11 15:16:55.522354+02	2026-09-11 15:16:55.522754+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.522405+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002875328063964844, \\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.522738+02:00\\"}"}	dry	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key1],v=1"}
8c548bf5-c5a3-4c40-8ea9-b7b897e69c3d	dryrun	2026-09-11 15:16:55.526605+02	2026-09-11 15:16:55.526917+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.526652+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002181529998779297, \\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.526906+02:00\\"}"}	dry	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key3],v=1"}
e3dc0ec6-68ce-46df-9ec7-a47df9ea59f5	dryrun	2026-09-11 15:16:55.529302+02	2026-09-11 15:16:55.529629+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.529350+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 6b7912e3-d74a-46b4-91db-d5d86aedb14a - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00022602081298828125, \\"dry_run_id\\": \\"6b7912e3-d74a-46b4-91db-d5d86aedb14a\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.529616+02:00\\"}"}	dry	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	1	{"test::Resource[agent1,key=key5],v=1"}
bc9ace31-1208-4352-a0cf-06a416fe8d96	store	2026-09-11 15:16:55.68422+02	2026-09-11 15:16:55.685982+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-09-11T15:16:55.685989+02:00\\"}"}	\N	\N	\N	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3	{"test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3"}
5bfa3a81-809c-4cfc-a126-0b9040cb1a4c	deploy	2026-09-11 15:16:55.542906+02	2026-09-11 15:16:55.548305+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 687b7b39-7061-4146-beb7-c42a72f85320).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"687b7b39-7061-4146-beb7-c42a72f85320\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.544578+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.544878+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 687b7b39-7061-4146-beb7-c42a72f85320) - duration: 0.0036 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.003635406494140625, \\"deploy_id\\": \\"687b7b39-7061-4146-beb7-c42a72f85320\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.548269+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	{"test::Resource[agent1,key=key10],v=2"}
b703e837-baf6-4b0e-9c33-0d0944f709ea	deploy	2026-09-11 15:16:55.550105+02	2026-09-11 15:16:55.553299+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: cc7627fa-93a1-4e79-b3ac-865c9183398b).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"cc7627fa-93a1-4e79-b3ac-865c9183398b\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.550768+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.550966+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: cc7627fa-93a1-4e79-b3ac-865c9183398b) - duration: 0.0025 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.0024614334106445312, \\"deploy_id\\": \\"cc7627fa-93a1-4e79-b3ac-865c9183398b\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.553270+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	{"test::Resource[agent1,key=key11],v=2"}
5248db3e-a68f-43e8-aa76-d36a4a38c098	deploy	2026-09-11 15:16:55.554239+02	2026-09-11 15:16:55.557229+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ea1a31ac-23da-4439-a68f-007348c300ec).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"ea1a31ac-23da-4439-a68f-007348c300ec\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.554798+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: ea1a31ac-23da-4439-a68f-007348c300ec) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.002365589141845703, \\"deploy_id\\": \\"ea1a31ac-23da-4439-a68f-007348c300ec\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.557202+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	{"test::Resource[agent1,key=key7],v=2"}
37b29731-8f05-4143-aff8-3d6a35be4820	deploy	2026-09-11 15:16:55.557944+02	2026-09-11 15:16:55.560827+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 6dbdfd1e-c5dd-4d02-b7fb-72a6d250c4c8).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"6dbdfd1e-c5dd-4d02-b7fb-72a6d250c4c8\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.558497+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 6dbdfd1e-c5dd-4d02-b7fb-72a6d250c4c8) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0022644996643066406, \\"deploy_id\\": \\"6dbdfd1e-c5dd-4d02-b7fb-72a6d250c4c8\\"}, \\"timestamp\\": \\"2026-09-11T15:16:55.560800+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2	{"test::Resource[agent1,key=key9],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	eef68eb1-f104-47f9-b19e-321183e3356b	fs::File[localhost,path=/tmp/test]	1
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	eef68eb1-f104-47f9-b19e-321183e3356b	std::AgentConfig[internal,agentname=localhost]	1
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	c1ba98c8-5bca-46cf-ac90-c0a10b7448f5	std::AgentConfig[internal,agentname=localhost]	1
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	5449a91a-bdb9-47ec-8196-8f3495cd369e	fs::File[localhost,path=/tmp/test]	1
813f0711-6e78-43fd-ae4b-7911fd102d24	4abe9e1c-b4bb-42f3-a3ac-81dd599bb682	fs::File[localhost,path=/tmp/test]	1
813f0711-6e78-43fd-ae4b-7911fd102d24	4abe9e1c-b4bb-42f3-a3ac-81dd599bb682	std::AgentConfig[internal,agentname=localhost]	1
813f0711-6e78-43fd-ae4b-7911fd102d24	8558f0ef-d693-401c-9d12-204ab40882a5	std::AgentConfig[internal,agentname=localhost]	1
813f0711-6e78-43fd-ae4b-7911fd102d24	c78058b2-20c4-4e3e-b8f7-02101e1156f3	fs::File[localhost,path=/tmp/test]	1
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	17dec0ac-f0b1-472c-9823-411faf50b999	std::AgentConfig[internal,agentname=localhost]	2
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	17dec0ac-f0b1-472c-9823-411faf50b999	fs::File[localhost,path=/tmp/test]	2
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	eb526918-3d8e-4b03-b293-6ffd5eb38b57	std::AgentConfig[internal,agentname=localhost]	3
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	eb526918-3d8e-4b03-b293-6ffd5eb38b57	fs::File[localhost,path=/tmp/test_orphan]	3
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	eb526918-3d8e-4b03-b293-6ffd5eb38b57	fs::File[localhost,path=/tmp/test]	3
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	e86ba7c1-0a35-4e2c-9e0f-c606fa5e4d34	fs::File[localhost,path=/tmp/test_orphan]	3
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	32fbc0cc-f50d-4ad1-b5ad-ad51fdce728d	std::AgentConfig[internal,agentname=localhost]	4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	32fbc0cc-f50d-4ad1-b5ad-ad51fdce728d	fs::File[localhost,path=/tmp/test]	4
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3f9f597b-504e-4a1b-9804-afb1f16701c0	std::AgentConfig[internal,agentname=localhost]	5
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	3f9f597b-504e-4a1b-9804-afb1f16701c0	fs::File[localhost,path=/tmp/test]	5
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	e75c64ca-348e-48ed-b370-864280c123f6	std::AgentConfig[internal,agentname=localhost]	6
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	e75c64ca-348e-48ed-b370-864280c123f6	fs::File[localhost,path=/tmp/test]	6
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	d5462da2-2fe5-4da2-88d5-aa4b71b9edba	std::AgentConfig[internal,agentname=localhost]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	d5462da2-2fe5-4da2-88d5-aa4b71b9edba	fs::File[localhost,path=/tmp/test]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	d5462da2-2fe5-4da2-88d5-aa4b71b9edba	test::Resource[agent3,key=key3]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	d5462da2-2fe5-4da2-88d5-aa4b71b9edba	test::Resource[agent2,key=key2]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	874f349b-dc8d-44f4-a4f2-dc8fc902622f	test::Resource[agent3,key=key3]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	316a4ebe-5bc7-4bea-9061-4f7917218aae	test::Resource[agent2,key=key2]	7
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	52b34b9d-99f9-4d91-b204-075bb5b40f2d	fs::File[localhost,path=/tmp/test]	8
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	52b34b9d-99f9-4d91-b204-075bb5b40f2d	test::Resource[agent2,key=key2]	8
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	52b34b9d-99f9-4d91-b204-075bb5b40f2d	std::AgentConfig[internal,agentname=localhost]	8
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Resource[agent1,key=key5]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Fail[agent1,key=key2]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Resource[agent1,key=key6]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Resource[agent1,key=key1]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Resource[agent1,key=key4]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	3cb1d528-3236-4864-ad4f-cfb2e485ac62	test::Resource[agent1,key=key3]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	9d5a7cde-2fae-41a2-92b8-eb8887b51aae	test::Resource[agent1,key=key1]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	cba990cb-fa55-41a9-8ac6-a9ff1adbe8be	test::Resource[agent1,key=key6]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	302293c6-45b7-4a4f-aa3d-e5a3ffad98d2	test::Fail[agent1,key=key2]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	9f5ca130-1402-4c5b-b92f-58d4c83d2813	test::Resource[agent1,key=key3]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	dfa74a80-889e-4e26-86f2-5e57a7cb56ba	test::Fail[agent1,key=key2]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	be2d536b-62a7-4989-b17b-3f9a8539715b	test::Resource[agent1,key=key1]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	8c548bf5-c5a3-4c40-8ea9-b7b897e69c3d	test::Resource[agent1,key=key3]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key3]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key5]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Fail[agent1,key=key2]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key9]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key7]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key11]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key1]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key10]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	379c4a2a-f360-4a22-b471-996ab596c85e	test::Resource[agent1,key=key4]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	e3dc0ec6-68ce-46df-9ec7-a47df9ea59f5	test::Resource[agent1,key=key5]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	0089e26c-d7bf-40d2-9ec4-a52db6e28f92	test::Resource[agent1,key=key6]	1
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	5bfa3a81-809c-4cfc-a126-0b9040cb1a4c	test::Resource[agent1,key=key10]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	b703e837-baf6-4b0e-9c33-0d0944f709ea	test::Resource[agent1,key=key11]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	5248db3e-a68f-43e8-aa76-d36a4a38c098	test::Resource[agent1,key=key7]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	37b29731-8f05-4143-aff8-3d6a35be4820	test::Resource[agent1,key=key9]	2
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key7]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key8]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key3]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key1]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key4]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Resource[agent1,key=key5]	3
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	bc9ace31-1208-4352-a0cf-06a416fe8d96	test::Fail[agent1,key=key2]	3
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
813f0711-6e78-43fd-ae4b-7911fd102d24	1
d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	8
0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	d2b23b2e-459a-4abe-9ff6-d9828a1f5cf3	2026-09-11 15:16:08.096652+02	\N	9a8b3c94-f214-42fc-b689-89a01a439d0c
hugo-Latitude-5421	813f0711-6e78-43fd-ae4b-7911fd102d24	2026-09-11 15:16:08.204236+02	\N	dc5c64cc-a325-44df-84a8-7325c7b683ad
hugo-Latitude-5421	0f20ddcc-8af4-48cd-b631-4e3bca31fb12	2026-09-11 15:16:55.216875+02	2026-09-11 15:16:55.679492+02	41fda58e-ddd6-460e-8f31-6d8f15e532de
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

