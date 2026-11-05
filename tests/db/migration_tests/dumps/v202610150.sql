--
-- PostgreSQL database dump
--

--\restrict qZTTEgwwya86F6UNHuCv5e8T3H8YoiLobV5Rshv5DuH0QDVSg4Tyc6aGHphID1a

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
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	$__scheduler	f	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	$__scheduler	f	\N
03159b4f-1448-4331-9f42-8aa6b0cc42ab	$__scheduler	f	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	localhost	f	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	internal	f	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	localhost	f	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	agent3	f	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	agent2	f	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	agent1	t	t
a0039d95-cc53-4786-9d02-ed2485d51e3e	$__scheduler	t	t
b89b6766-005d-435e-beab-af7d5138b8fb	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
1	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
1	internal	std	c70de86e-2526-4c81-a1e7-38e1840e5778
1	localhost	fs	c70de86e-2526-4c81-a1e7-38e1840e5778
2	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
2	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
3	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
3	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
4	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
4	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
5	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
5	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
6	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
6	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
7	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
7	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
8	localhost	fs	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
8	localhost	std	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
df77469d-3f1a-4367-93d6-f65bee733737	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:32.719231+00	2026-10-15 15:24:39.330537+00	2026-10-15 15:24:32.673162+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	3ac443cc-4ea7-4d8b-b2b6-be6af4f64901	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
902316f0-6ca1-47c8-8691-8b56185c0a1b	c70de86e-2526-4c81-a1e7-38e1840e5778	2026-10-15 15:24:39.607817+00	2026-10-15 15:24:44.467481+00	2026-10-15 15:24:39.582857+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	44a11f1d-d5b8-40e5-a83d-0ea38d530211	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
4e38fd74-ef49-458d-9ed3-474786d53ee0	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:44.774013+00	2026-10-15 15:24:45.868194+00	2026-10-15 15:24:44.749227+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	a6e613c2-98aa-4f16-972c-1b8ec178ca4d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
17ec0e33-a3a4-4d83-ab81-79342a028837	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:45.9833+00	2026-10-15 15:24:47.080863+00	2026-10-15 15:24:45.963161+00	{}	{"add_one_resource": "true"}	t	f	t	3	b4ac3eda-71b6-4efc-ab8b-544fb3e3b1b4	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
1ee34ec6-6290-4b64-9539-1f970ce25049	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:47.364552+00	2026-10-15 15:24:48.46622+00	2026-10-15 15:24:47.348513+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	200b64a5-336d-4f17-b3e1-461869e56528	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
9b8b8915-54b8-45b4-a09c-59881eb3eb36	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:48.65459+00	2026-10-15 15:24:49.752175+00	2026-10-15 15:24:48.64231+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	b8a41969-7b39-4bb6-ac99-2c0cb0cf8f8a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
73fc863f-b6db-47fd-9cd1-ceb02461600b	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:49.890692+00	2026-10-15 15:24:54.076834+00	2026-10-15 15:24:49.877294+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	5f5ef8e4-7e7c-4a73-96c5-7edb4483beeb	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
10c030b5-5134-4b3f-843d-7be6ca373ada	b89b6766-005d-435e-beab-af7d5138b8fb	2026-10-15 15:24:55.597472+00	2026-10-15 15:24:55.643651+00	2026-10-15 15:24:55.544899+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	813364e4-c2fb-4f98-93ee-52e1282c3db0	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:39.263234+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	a0039d95-cc53-4786-9d02-ed2485d51e3e	2026-10-15 15:24:54.692172+00	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
1	c70de86e-2526-4c81-a1e7-38e1840e5778	2026-10-15 15:24:44.402582+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:45.808423+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:47.020529+00	t	{"export_metadata": {"type": "manual", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:48.40218+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:49.700211+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:54.033997+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
2	a0039d95-cc53-4786-9d02-ed2485d51e3e	2026-10-15 15:24:55.027625+00	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:54.208085+00	t	\N	3	{}	{}	6	t	\N	\N
8	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:54.412169+00	t	\N	2	{}	{}	7	t	\N	\N
3	a0039d95-cc53-4786-9d02-ed2485d51e3e	2026-10-15 15:24:55.331202+00	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	1	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	1	fs	1.2.0
c70de86e-2526-4c81-a1e7-38e1840e5778	1	std	7.0.0
c70de86e-2526-4c81-a1e7-38e1840e5778	1	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	4	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	4	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	5	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	5	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	6	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	6	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	std	8.7.5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8	fs	1.2.0
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	discovery::Discovered[myagent,name=discovered]	{}	2026-10-15 15:24:55.357899+00	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-15 15:24:55.357971+00	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
783880a6-7b64-4807-be98-e200c642e0e3	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	2026-10-15 15:24:54.977094+00	6	0	{"266a8052-7c1c-5b81-b1a9-c644b477e497": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "3159e2ad-49b3-573c-b5fb-bf96ee26fffa": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "6f88af4c-a8d8-5642-9a3e-27510a9f1911": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "81c355a6-accd-53e1-8b06-624a6385e01e": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "e36c10cc-0b8a-5d1f-b4ee-ece1f78b1656": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "f6f6440d-9e6b-5865-b2a0-13dfe406b65f": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
b89b6766-005d-435e-beab-af7d5138b8fb	dev-4	f2af65b0-5165-4169-8e9e-639651f7ff29			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	dev-1	f2af65b0-5165-4169-8e9e-639651f7ff29			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
c70de86e-2526-4c81-a1e7-38e1840e5778	dev-1-twin	f2af65b0-5165-4169-8e9e-639651f7ff29			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
03159b4f-1448-4331-9f42-8aa6b0cc42ab	dev-2	f2af65b0-5165-4169-8e9e-639651f7ff29			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
a0039d95-cc53-4786-9d02-ed2485d51e3e	dev-3	f2af65b0-5165-4169-8e9e-639651f7ff29			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	\N	f
fs	1.2.0	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	\N	f
std	7.0.0	c70de86e-2526-4c81-a1e7-38e1840e5778	\N	f
fs	1.2.0	c70de86e-2526-4c81-a1e7-38e1840e5778	\N	f
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
ad9bc318-9597-409c-9f13-2deb08de5166	b89b6766-005d-435e-beab-af7d5138b8fb	2026-10-15 15:24:55.655908+00	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/10c030b5-5134-4b3f-843d-7be6ca373ada	f	f	10c030b5-5134-4b3f-843d-7be6ca373ada
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
7290d362-2ea8-4ca7-bc88-4bfa000994b9	fact1	value1	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	std::testing::NullResource[localhost,name=test1]	fact	2026-10-15 15:24:48.572073+00	{}	f
7e2b5e35-b249-4f56-a774-0ebcd55de043	fact2	value2	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	std::testing::NullResource[localhost,name=test2]	fact	2026-10-15 15:24:48.591449+00	{}	t
929c1dee-1a65-4bd7-98ae-682e777e29a8	fact3	value3	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	std::testing::NullResource[localhost,name=test3]	fact	2026-10-15 15:24:48.6024+00	{}	t
3ea02b9b-0c87-4596-840a-ff40935e0efc	parameter1	value1	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2		fact	2026-10-15 15:24:48.612758+00	{}	f
d1f92630-2148-4047-9778-51993c4edaf9	parameter2	value2	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2		fact	2026-10-15 15:24:48.622599+00	{}	f
00c6396c-5010-4dce-9bf2-75ba9df9162b	parameter3	value3	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2		fact	2026-10-15 15:24:48.632495+00	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
f2af65b0-5165-4169-8e9e-639651f7ff29	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
42b05e21-df30-44f0-b6ba-2fea3d90dcd9	2026-10-15 15:24:32.726726+00	2026-10-15 15:24:32.746631+00		Init		Using extra environment variables during compile \n	0	df77469d-3f1a-4367-93d6-f65bee733737
c1a28877-9e0e-4774-9854-927aef6c9233	2026-10-15 15:24:32.754914+00	2026-10-15 15:24:32.775139+00		Venv check		Creating new venv at /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env-py3.14\n	0	df77469d-3f1a-4367-93d6-f65bee733737
f1d09bab-190a-49a3-b1a2-a457f8a9a8a0	2026-10-15 15:24:39.616686+00	2026-10-15 15:24:39.642126+00		Init		Using extra environment variables during compile \n	0	902316f0-6ca1-47c8-8691-8b56185c0a1b
b47b2865-e924-4865-b217-b40af9ac43fc	2026-10-15 15:24:39.65113+00	2026-10-15 15:24:39.672292+00		Venv check		Creating new venv at /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env-py3.14\n	0	902316f0-6ca1-47c8-8691-8b56185c0a1b
08686e3b-1d1f-405d-85b8-1f911ce1ff23	2026-10-15 15:24:32.785326+00	2026-10-15 15:24:33.006702+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	df77469d-3f1a-4367-93d6-f65bee733737
0d292d70-8325-4659-9a6b-d1ba13f9c8cc	2026-10-15 15:24:39.682288+00	2026-10-15 15:24:39.90166+00	/tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	902316f0-6ca1-47c8-8691-8b56185c0a1b
8d97f007-d3dd-46cb-822c-45a95d9b32dd	2026-10-15 15:24:45.991755+00	2026-10-15 15:24:46.014614+00		Init		Using extra environment variables during compile add_one_resource='true'\n	0	17ec0e33-a3a4-4d83-ab81-79342a028837
a8f42b8e-62ea-4863-b5cf-6c7547af03bb	2026-10-15 15:24:43.460755+00	2026-10-15 15:24:44.458876+00	/tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c70de86e-2526-4c81-a1e7-38e1840e5778 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppj_t5jv3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.008 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.032 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.057 seconds\ncompiler       DEBUG   The entire export command took 0.118 seconds\n	0	902316f0-6ca1-47c8-8691-8b56185c0a1b
67a66c38-5d3e-4966-8a10-6f5455410804	2026-10-15 15:24:46.023185+00	2026-10-15 15:24:46.041191+00		Venv check		Found existing venv\n	0	17ec0e33-a3a4-4d83-ab81-79342a028837
384fdec1-0558-4fc2-84a7-07d24ae225d7	2026-10-15 15:24:44.782271+00	2026-10-15 15:24:44.803849+00		Init		Using extra environment variables during compile \n	0	4e38fd74-ef49-458d-9ed3-474786d53ee0
f2d67467-9932-4bb5-ac30-b2901805bc03	2026-10-15 15:24:38.270413+00	2026-10-15 15:24:39.322904+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp8xnq37x5 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.017 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.033 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.083 seconds\ncompiler       DEBUG   The entire export command took 0.156 seconds\n	0	df77469d-3f1a-4367-93d6-f65bee733737
cbcc97da-7458-4246-9300-68d6c0326927	2026-10-15 15:24:33.014698+00	2026-10-15 15:24:38.262229+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpfwvppcpv:\n                                 Pip command: /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpfwvppcpv inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl.metadata (42 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl.metadata (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.334.4)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: pydantic-core, more-itertools, mitogen, strawberry-graphql, pydantic, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.2.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.334.4\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.54 more-itertools-11.2.1 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.335.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	df77469d-3f1a-4367-93d6-f65bee733737
3e9dacf3-d717-47e5-be06-e301cf9d8cbe	2026-10-15 15:24:44.812633+00	2026-10-15 15:24:44.83083+00		Venv check		Found existing venv\n	0	4e38fd74-ef49-458d-9ed3-474786d53ee0
624ba05e-a754-4472-9571-7086be7dd393	2026-10-15 15:24:47.37193+00	2026-10-15 15:24:47.394277+00		Init		Using extra environment variables during compile \n	0	1ee34ec6-6290-4b64-9539-1f970ce25049
cd6632ba-9733-4f62-b674-774f83939587	2026-10-15 15:24:47.402782+00	2026-10-15 15:24:47.420638+00		Venv check		Found existing venv\n	0	1ee34ec6-6290-4b64-9539-1f970ce25049
12e9dbcb-0fea-44ba-b20c-ee99ebf759fd	2026-10-15 15:24:44.840927+00	2026-10-15 15:24:45.858469+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp0cebkai4 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.051 seconds\ncompiler       DEBUG   The entire export command took 0.120 seconds\n	0	4e38fd74-ef49-458d-9ed3-474786d53ee0
84bd04a6-e1f9-4743-aae5-cd399aabcbf5	2026-10-15 15:24:47.429936+00	2026-10-15 15:24:48.458571+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpp5msd3n6 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.033 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.057 seconds\ncompiler       DEBUG   The entire export command took 0.125 seconds\n	0	1ee34ec6-6290-4b64-9539-1f970ce25049
5d07caac-b7f6-47fc-a9b2-abc8f0031eb8	2026-10-15 15:24:49.948291+00	2026-10-15 15:24:50.171612+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	73fc863f-b6db-47fd-9cd1-ceb02461600b
530530b2-02b5-4bc7-804f-b9a0610ef1d8	2026-10-15 15:24:46.049946+00	2026-10-15 15:24:47.071644+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpgt9aa0xg --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.032 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.069 seconds\ncompiler       DEBUG   The entire export command took 0.135 seconds\n	0	17ec0e33-a3a4-4d83-ab81-79342a028837
ec92eb03-1189-42a0-8e98-c37dd979a436	2026-10-15 15:24:49.897681+00	2026-10-15 15:24:49.914656+00		Init		Using extra environment variables during compile \n	0	73fc863f-b6db-47fd-9cd1-ceb02461600b
7a0a7714-6490-4e7e-9d58-be787618ea4e	2026-10-15 15:24:49.922503+00	2026-10-15 15:24:49.938157+00		Venv check		Found existing venv\n	0	73fc863f-b6db-47fd-9cd1-ceb02461600b
5961bcee-5cd7-480f-a2a1-00c44e8b9317	2026-10-15 15:24:48.717016+00	2026-10-15 15:24:49.743019+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpmsz73jod --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.042 seconds\ncompiler       DEBUG   The entire export command took 0.112 seconds\n	0	9b8b8915-54b8-45b4-a09c-59881eb3eb36
4f0caa2a-c3d7-4f97-9bd0-28c43d73d42d	2026-10-15 15:24:39.909296+00	2026-10-15 15:24:43.453193+00	/tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpokuiw6nk:\n                                 Pip command: /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpokuiw6nk inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl.metadata (42 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl.metadata (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.334.4)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: pydantic-core, more-itertools, mitogen, strawberry-graphql, pydantic, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.2.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.334.4\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp8xtunl9k/server/c70de86e-2526-4c81-a1e7-38e1840e5778/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.54 more-itertools-11.2.1 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.335.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	902316f0-6ca1-47c8-8691-8b56185c0a1b
168feb71-2fed-4724-947f-d85cedd39e51	2026-10-15 15:24:48.66124+00	2026-10-15 15:24:48.682554+00		Init		Using extra environment variables during compile \n	0	9b8b8915-54b8-45b4-a09c-59881eb3eb36
9495c796-a26b-4dd2-992d-8ed8d8846371	2026-10-15 15:24:48.690757+00	2026-10-15 15:24:48.708365+00		Venv check		Found existing venv\n	0	9b8b8915-54b8-45b4-a09c-59881eb3eb36
abf56af3-513d-493b-bd13-2d883940b2b8	2026-10-15 15:24:53.063647+00	2026-10-15 15:24:54.069332+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2 --server_address localhost --server_port 34195 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpiw9_bsmb --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.037 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34195/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34195/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.045 seconds\ncompiler       DEBUG   The entire export command took 0.116 seconds\n	0	73fc863f-b6db-47fd-9cd1-ceb02461600b
216c439e-e848-459d-9d04-0eb4be95c5b8	2026-10-15 15:24:50.179676+00	2026-10-15 15:24:53.055559+00	/tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpbbgz7o06:\n                                 Pip command: /tmp/tmp8xtunl9k/server/5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpbbgz7o06 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in ./.env/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in ./.env/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.335.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	73fc863f-b6db-47fd-9cd1-ceb02461600b
91ff851a-1b0c-4bfe-bd8f-24e7f012b3d7	2026-10-15 15:24:55.60784+00	2026-10-15 15:24:55.635221+00		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp8xtunl9k/server/b89b6766-005d-435e-beab-af7d5138b8fb/compiler and no repository set.\n	1	10c030b5-5134-4b3f-843d-7be6ca373ada
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	08036ce2-ce4d-4322-91ce-cf74e4ee722a
c70de86e-2526-4c81-a1e7-38e1840e5778	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	2f449f5d-b630-4680-a07f-ced39057ffcc
c70de86e-2526-4c81-a1e7-38e1840e5778	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	2f449f5d-b630-4680-a07f-ced39057ffcc
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	f0639370-f60f-4fa0-a98f-80bdab574ad9
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	b5b305aa-bed8-424e-a01c-6564c503397a
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	b5b305aa-bed8-424e-a01c-6564c503397a
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	09db7afc-5f1f-4b0b-a3c4-d0b488cdf288
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	4a140f6c-8570-4871-a263-01933bd3c131
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7c8eb1dd-10d5-4300-a45d-18a701ad8cfd
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	c7a069f2-bc45-4b7c-8d5d-c66e6ba11f42
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	a352df7c-ad19-4d53-9181-70c649d1043b
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	5b75b9b7-5443-480c-8693-f917e86dda29
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7ee95fb3-1726-43a0-b32b-701abfb92a06
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	00db906c-48c7-4a1f-a1e8-0619489c3067
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	36a209c5-671d-4407-b377-baf79a146050
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	36a209c5-671d-4407-b377-baf79a146050
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
e4e430ef-e50d-43ef-b04a-324ca283eee8	a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-15 15:24:55.164001+00
b7496e09-4a9f-4694-91ec-2f6999e2fc4d	a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-15 15:24:55.204859+00
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Fail[agent1,key=key2]	2026-10-15 15:24:54.760759+00	\N	2026-10-15 15:24:54.760759+00	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:54.71129+00	f	\N	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test]	2026-10-15 15:24:39.473646+00	\N	2026-10-15 15:24:39.473646+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:39.438862+00	f	\N	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key11]	2026-10-15 15:24:55.164001+00	\N	2026-10-15 15:24:55.164001+00	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:55.05001+00	f	e4e430ef-e50d-43ef-b04a-324ca283eee8	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key3]	2026-10-15 15:24:54.790983+00	\N	2026-10-15 15:24:54.790983+00	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-15 15:24:54.71129+00	f	\N	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	std::AgentConfig[internal,agentname=localhost]	2026-10-15 15:24:44.662999+00	\N	2026-10-15 15:24:44.662999+00	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:44.614956+00	f	\N	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key1]	2026-10-15 15:24:54.826501+00	2026-10-15 15:24:54.80167+00	2026-10-15 15:24:54.826501+00	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:54.71129+00	t	\N	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	fs::File[localhost,path=/tmp/test]	2026-10-15 15:24:44.697191+00	\N	2026-10-15 15:24:44.697191+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:44.614956+00	f	\N	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key9]	2026-10-15 15:24:55.18597+00	2026-10-15 15:24:55.173002+00	2026-10-15 15:24:55.18597+00	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:55.05001+00	t	\N	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	fs::File[localhost,path=/tmp/test_orphan]	2026-10-15 15:24:47.237123+00	\N	2026-10-15 15:24:47.237123+00	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:47.208568+00	f	\N	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key10]	2026-10-15 15:24:55.204859+00	\N	2026-10-15 15:24:55.204859+00	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:55.05001+00	f	b7496e09-4a9f-4694-91ec-2f6999e2fc4d	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	test::Resource[agent2,key=key2]	2026-10-15 15:24:54.292243+00	\N	2026-10-15 15:24:54.292243+00	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:54.263835+00	f	\N	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	test::Resource[agent3,key=key3]	2026-10-15 15:24:54.305596+00	\N	2026-10-15 15:24:54.305596+00	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-15 15:24:54.263835+00	f	\N	7
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-15 15:24:54.71129+00	\N	\N	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-15 15:24:54.71129+00	\N	\N	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key6]	2026-10-15 15:24:54.850591+00	2026-10-15 15:24:54.836774+00	2026-10-15 15:24:54.850591+00	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:54.71129+00	t	\N	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	test::Resource[agent1,key=key7]	2026-10-15 15:24:55.136116+00	2026-10-15 15:24:55.108739+00	2026-10-15 15:24:55.136116+00	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 15:24:55.05001+00	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	08036ce2-ce4d-4322-91ce-cf74e4ee722a	\N
c70de86e-2526-4c81-a1e7-38e1840e5778	2f449f5d-b630-4680-a07f-ced39057ffcc	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	f0639370-f60f-4fa0-a98f-80bdab574ad9	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	b5b305aa-bed8-424e-a01c-6564c503397a	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	09db7afc-5f1f-4b0b-a3c4-d0b488cdf288	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	4a140f6c-8570-4871-a263-01933bd3c131	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7c8eb1dd-10d5-4300-a45d-18a701ad8cfd	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	c7a069f2-bc45-4b7c-8d5d-c66e6ba11f42	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	a352df7c-ad19-4d53-9181-70c649d1043b	set-b
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	5b75b9b7-5443-480c-8693-f917e86dda29	set-a
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7ee95fb3-1726-43a0-b32b-701abfb92a06	\N
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	00db906c-48c7-4a1f-a1e8-0619489c3067	set-a
a0039d95-cc53-4786-9d02-ed2485d51e3e	f02ea434-37b1-4f1f-9baa-93e36b73cd31	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	57f19174-ea45-48f1-89c2-d6e21459189e	\N
a0039d95-cc53-4786-9d02-ed2485d51e3e	36a209c5-671d-4407-b377-baf79a146050	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	1	08036ce2-ce4d-4322-91ce-cf74e4ee722a
c70de86e-2526-4c81-a1e7-38e1840e5778	1	2f449f5d-b630-4680-a07f-ced39057ffcc
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2	f0639370-f60f-4fa0-a98f-80bdab574ad9
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3	b5b305aa-bed8-424e-a01c-6564c503397a
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	4	09db7afc-5f1f-4b0b-a3c4-d0b488cdf288
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	5	4a140f6c-8570-4871-a263-01933bd3c131
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	6	7c8eb1dd-10d5-4300-a45d-18a701ad8cfd
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	c7a069f2-bc45-4b7c-8d5d-c66e6ba11f42
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	a352df7c-ad19-4d53-9181-70c649d1043b
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	5b75b9b7-5443-480c-8693-f917e86dda29
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8	7ee95fb3-1726-43a0-b32b-701abfb92a06
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8	00db906c-48c7-4a1f-a1e8-0619489c3067
a0039d95-cc53-4786-9d02-ed2485d51e3e	1	f02ea434-37b1-4f1f-9baa-93e36b73cd31
a0039d95-cc53-4786-9d02-ed2485d51e3e	2	57f19174-ea45-48f1-89c2-d6e21459189e
a0039d95-cc53-4786-9d02-ed2485d51e3e	3	36a209c5-671d-4407-b377-baf79a146050
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
d5ddfa72-26ed-4a41-983b-7aa995308e74	store	2026-10-15 15:24:39.263048+00	2026-10-15 15:24:39.28358+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T16:24:39.283604+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	1	{"fs::File[localhost,path=/tmp/test],v=1"}
d56d25d3-b512-48b5-867f-b9e7977954e3	deploy	2026-10-15 15:24:39.458418+00	2026-10-15 15:24:39.473646+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:39.472646+01:00\\"}"}	unavailable	\N	nochange	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	1	{"fs::File[localhost,path=/tmp/test],v=1"}
8958262a-b8f9-44c8-bb28-e9b835f73bc7	store	2026-10-15 15:24:44.402448+00	2026-10-15 15:24:44.425959+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T16:24:44.425982+01:00\\"}"}	\N	\N	\N	c70de86e-2526-4c81-a1e7-38e1840e5778	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
5ace1f60-7e3b-46b8-b00e-8d7131feb0b6	deploy	2026-10-15 15:24:44.637206+00	2026-10-15 15:24:44.662999+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:44.661305+01:00\\"}"}	unavailable	\N	nochange	c70de86e-2526-4c81-a1e7-38e1840e5778	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
eb3376a4-3c09-4d45-bf8a-eae197acc4c7	deploy	2026-10-15 15:24:44.687864+00	2026-10-15 15:24:44.697191+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:44.696086+01:00\\"}"}	unavailable	\N	nochange	c70de86e-2526-4c81-a1e7-38e1840e5778	1	{"fs::File[localhost,path=/tmp/test],v=1"}
67cd0b20-14cd-4ffc-b9bd-8fb4a1148316	store	2026-10-15 15:24:45.807794+00	2026-10-15 15:24:45.82126+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-15T16:24:45.821297+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2	{"fs::File[localhost,path=/tmp/test],v=2"}
9a5b464b-44f8-4d38-833b-3878c8567822	store	2026-10-15 15:24:47.020092+00	2026-10-15 15:24:47.033383+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-15T16:24:47.033426+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
e8b90ba7-5414-4aaf-9017-37cb4bc6befc	deploy	2026-10-15 15:24:47.221049+00	2026-10-15 15:24:47.237123+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-15T16:24:47.236419+01:00\\"}"}	unavailable	\N	nochange	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
f9f1f1a3-6ed0-4208-81c1-a0b57f8bdc21	store	2026-10-15 15:24:48.40177+00	2026-10-15 15:24:48.419786+00	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-15T16:24:48.419814+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	4	{"fs::File[localhost,path=/tmp/test],v=4"}
ff9831e9-187c-46ff-9989-be5e20b49464	store	2026-10-15 15:24:49.699941+00	2026-10-15 15:24:49.707182+00	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-15T16:24:49.707200+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	5	{"fs::File[localhost,path=/tmp/test],v=5"}
710a5ed5-02a2-4282-96c1-082b8f11d96c	store	2026-10-15 15:24:54.033772+00	2026-10-15 15:24:54.038858+00	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-15T16:24:54.038881+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	6	{"fs::File[localhost,path=/tmp/test],v=6"}
b9889b57-0367-42aa-bca7-343d3f561662	store	2026-10-15 15:24:54.207897+00	2026-10-15 15:24:54.217316+00	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-15T16:24:54.217333+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7"}
3cdf76ce-c272-4986-a8f7-0c5d9e119338	deploy	2026-10-15 15:24:54.278163+00	2026-10-15 15:24:54.292243+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.291224+01:00\\"}"}	unavailable	\N	nochange	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	{"test::Resource[agent2,key=key2],v=7"}
884924fb-5fda-4438-9083-e5eabf2704ce	deploy	2026-10-15 15:24:54.292365+00	2026-10-15 15:24:54.305596+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.303933+01:00\\"}"}	unavailable	\N	nochange	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	7	{"test::Resource[agent3,key=key3],v=7"}
d82467e0-271f-4aad-9295-459a3b85b179	store	2026-10-15 15:24:54.412062+00	2026-10-15 15:24:54.417924+00	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-15T16:24:54.417944+01:00\\"}"}	\N	\N	\N	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
07707be6-0845-4b2c-b0c7-a2f86ed008ab	store	2026-10-15 15:24:54.69206+00	2026-10-15 15:24:54.696512+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T16:24:54.696528+01:00\\"}"}	\N	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key1],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key6],v=1"}
3cbba2b0-61d6-4bc4-8566-0140597e5508	deploy	2026-10-15 15:24:54.742523+00	2026-10-15 15:24:54.760759+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1f8bf9b0-f988-4962-8bb7-cc49540511dd).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"1f8bf9b0-f988-4962-8bb7-cc49540511dd\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.756942+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core-dryrun-context/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core-dryrun-context/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.759230+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 1f8bf9b0-f988-4962-8bb7-cc49540511dd) - duration: 0.0035 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0035119056701660156, \\"deploy_id\\": \\"1f8bf9b0-f988-4962-8bb7-cc49540511dd\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.760653+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Fail[agent1,key=key2],v=1"}
b3976611-f593-422c-8ba3-6733ddc76d29	deploy	2026-10-15 15:24:54.777474+00	2026-10-15 15:24:54.790983+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f95b0a6d-18c0-4f58-b7ab-fa4d18d59a44).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"f95b0a6d-18c0-4f58-b7ab-fa4d18d59a44\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.790204+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.790532+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: f95b0a6d-18c0-4f58-b7ab-fa4d18d59a44) - duration: 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0004913806915283203, \\"deploy_id\\": \\"f95b0a6d-18c0-4f58-b7ab-fa4d18d59a44\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.790882+01:00\\"}"}	skipped	\N	nochange	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key3],v=1"}
0c634c2e-a39c-47bf-b15a-e1d8300baee0	deploy	2026-10-15 15:24:54.801751+00	2026-10-15 15:24:54.826501+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: be948e54-2afd-4f6f-8f1a-5b7ff1ef1efa).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"be948e54-2afd-4f6f-8f1a-5b7ff1ef1efa\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.811533+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: be948e54-2afd-4f6f-8f1a-5b7ff1ef1efa) - duration: 0.0148 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.014797449111938477, \\"deploy_id\\": \\"be948e54-2afd-4f6f-8f1a-5b7ff1ef1efa\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.826439+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key1],v=1"}
4bd84bc1-05c2-42e0-ae30-65a01ea569d0	deploy	2026-10-15 15:24:54.836898+00	2026-10-15 15:24:54.850591+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 773fa31d-7c54-44fa-9270-227a0db21633).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"773fa31d-7c54-44fa-9270-227a0db21633\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.844994+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 773fa31d-7c54-44fa-9270-227a0db21633) - duration: 0.0054 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.00543522834777832, \\"deploy_id\\": \\"773fa31d-7c54-44fa-9270-227a0db21633\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.850527+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key6],v=1"}
0fd45fe0-92a9-44e0-a6c1-56bb64028580	dryrun	2026-10-15 15:24:54.989758+00	2026-10-15 15:24:54.990248+00	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.989857+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003154277801513672, \\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:54.990229+01:00\\"}"}	dry	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Fail[agent1,key=key2],v=1"}
31114351-07c4-44cd-be09-aca18c10eca6	dryrun	2026-10-15 15:24:55.029302+00	2026-10-15 15:24:55.02977+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.029377+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003070831298828125, \\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.029747+01:00\\"}"}	dry	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key1],v=1"}
5f27815b-c32d-44f2-889f-72e22f4da469	store	2026-10-15 15:24:55.027516+00	2026-10-15 15:24:55.031866+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-15T16:24:55.031876+01:00\\"}"}	\N	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	2	{"test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key3],v=2"}
0872a871-9858-488d-81e1-5daaa6161097	dryrun	2026-10-15 15:24:55.051313+00	2026-10-15 15:24:55.05189+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.051414+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003898143768310547, \\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.051869+01:00\\"}"}	dry	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key3],v=1"}
3cddd305-42e5-404b-95c0-213bb5e31a8f	deploy	2026-10-15 15:24:55.108895+00	2026-10-15 15:24:55.136116+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: eeaab705-425b-44a7-8685-535ab65190d6).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"eeaab705-425b-44a7-8685-535ab65190d6\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.119414+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: eeaab705-425b-44a7-8685-535ab65190d6) - duration: 0.0164 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.01643967628479004, \\"deploy_id\\": \\"eeaab705-425b-44a7-8685-535ab65190d6\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.136014+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	a0039d95-cc53-4786-9d02-ed2485d51e3e	2	{"test::Resource[agent1,key=key7],v=2"}
71c693bf-d892-428f-9a95-5e11b6453cfd	deploy	2026-10-15 15:24:55.147844+00	2026-10-15 15:24:55.164001+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 48eb08aa-0113-4faf-8bc2-2a7b7277bd86).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"48eb08aa-0113-4faf-8bc2-2a7b7277bd86\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.157824+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.158189+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 48eb08aa-0113-4faf-8bc2-2a7b7277bd86) - duration: 0.0060 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.006032466888427734, \\"deploy_id\\": \\"48eb08aa-0113-4faf-8bc2-2a7b7277bd86\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.163947+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	a0039d95-cc53-4786-9d02-ed2485d51e3e	2	{"test::Resource[agent1,key=key11],v=2"}
2155e7d7-164e-450b-872f-377c122d518d	deploy	2026-10-15 15:24:55.173093+00	2026-10-15 15:24:55.18597+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: c49bf6d7-a21f-4c31-98e3-58af14581c7d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"c49bf6d7-a21f-4c31-98e3-58af14581c7d\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.182195+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: c49bf6d7-a21f-4c31-98e3-58af14581c7d) - duration: 0.0037 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0036683082580566406, \\"deploy_id\\": \\"c49bf6d7-a21f-4c31-98e3-58af14581c7d\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.185927+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	a0039d95-cc53-4786-9d02-ed2485d51e3e	2	{"test::Resource[agent1,key=key9],v=2"}
0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	store	2026-10-15 15:24:55.331121+00	2026-10-15 15:24:55.335368+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-15T16:24:55.335384+01:00\\"}"}	\N	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	3	{"test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key7],v=3","test::Fail[agent1,key=key2],v=3"}
91187b9f-50c7-40fb-b866-b76712f812ae	deploy	2026-10-15 15:24:55.193206+00	2026-10-15 15:24:55.204859+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: a3c8a350-303c-4267-aee5-4c41c0146459).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"a3c8a350-303c-4267-aee5-4c41c0146459\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.200686+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.200975+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: a3c8a350-303c-4267-aee5-4c41c0146459) - duration: 0.0041 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.004052400588989258, \\"deploy_id\\": \\"a3c8a350-303c-4267-aee5-4c41c0146459\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.204817+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	a0039d95-cc53-4786-9d02-ed2485d51e3e	2	{"test::Resource[agent1,key=key10],v=2"}
eee2cd59-223d-4273-819c-0319bfca9058	dryrun	2026-10-15 15:24:55.21256+00	2026-10-15 15:24:55.213084+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.212648+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003578662872314453, \\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.213065+01:00\\"}"}	dry	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key5],v=1"}
556a27b3-adfc-425e-b536-cb1e50722cee	dryrun	2026-10-15 15:24:55.222713+00	2026-10-15 15:24:55.223112+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.222790+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 783880a6-7b64-4807-be98-e200c642e0e3 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00023293495178222656, \\"dry_run_id\\": \\"783880a6-7b64-4807-be98-e200c642e0e3\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-15T16:24:55.223094+01:00\\"}"}	dry	\N	\N	a0039d95-cc53-4786-9d02-ed2485d51e3e	1	{"test::Resource[agent1,key=key6],v=1"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	d5ddfa72-26ed-4a41-983b-7aa995308e74	fs::File[localhost,path=/tmp/test]	1
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	d56d25d3-b512-48b5-867f-b9e7977954e3	fs::File[localhost,path=/tmp/test]	1
c70de86e-2526-4c81-a1e7-38e1840e5778	8958262a-b8f9-44c8-bb28-e9b835f73bc7	std::AgentConfig[internal,agentname=localhost]	1
c70de86e-2526-4c81-a1e7-38e1840e5778	8958262a-b8f9-44c8-bb28-e9b835f73bc7	fs::File[localhost,path=/tmp/test]	1
c70de86e-2526-4c81-a1e7-38e1840e5778	5ace1f60-7e3b-46b8-b00e-8d7131feb0b6	std::AgentConfig[internal,agentname=localhost]	1
c70de86e-2526-4c81-a1e7-38e1840e5778	eb3376a4-3c09-4d45-bf8a-eae197acc4c7	fs::File[localhost,path=/tmp/test]	1
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	67cd0b20-14cd-4ffc-b9bd-8fb4a1148316	fs::File[localhost,path=/tmp/test]	2
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	9a5b464b-44f8-4d38-833b-3878c8567822	fs::File[localhost,path=/tmp/test_orphan]	3
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	9a5b464b-44f8-4d38-833b-3878c8567822	fs::File[localhost,path=/tmp/test]	3
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	e8b90ba7-5414-4aaf-9017-37cb4bc6befc	fs::File[localhost,path=/tmp/test_orphan]	3
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	f9f1f1a3-6ed0-4208-81c1-a0b57f8bdc21	fs::File[localhost,path=/tmp/test]	4
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	ff9831e9-187c-46ff-9989-be5e20b49464	fs::File[localhost,path=/tmp/test]	5
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	710a5ed5-02a2-4282-96c1-082b8f11d96c	fs::File[localhost,path=/tmp/test]	6
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	b9889b57-0367-42aa-bca7-343d3f561662	fs::File[localhost,path=/tmp/test]	7
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	b9889b57-0367-42aa-bca7-343d3f561662	test::Resource[agent2,key=key2]	7
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	b9889b57-0367-42aa-bca7-343d3f561662	test::Resource[agent3,key=key3]	7
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	3cdf76ce-c272-4986-a8f7-0c5d9e119338	test::Resource[agent2,key=key2]	7
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	884924fb-5fda-4438-9083-e5eabf2704ce	test::Resource[agent3,key=key3]	7
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	d82467e0-271f-4aad-9295-459a3b85b179	fs::File[localhost,path=/tmp/test]	8
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	d82467e0-271f-4aad-9295-459a3b85b179	test::Resource[agent2,key=key2]	8
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Resource[agent1,key=key1]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Fail[agent1,key=key2]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Resource[agent1,key=key5]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Resource[agent1,key=key4]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Resource[agent1,key=key3]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	07707be6-0845-4b2c-b0c7-a2f86ed008ab	test::Resource[agent1,key=key6]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	3cbba2b0-61d6-4bc4-8566-0140597e5508	test::Fail[agent1,key=key2]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	b3976611-f593-422c-8ba3-6733ddc76d29	test::Resource[agent1,key=key3]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	0c634c2e-a39c-47bf-b15a-e1d8300baee0	test::Resource[agent1,key=key1]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	4bd84bc1-05c2-42e0-ae30-65a01ea569d0	test::Resource[agent1,key=key6]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	0fd45fe0-92a9-44e0-a6c1-56bb64028580	test::Fail[agent1,key=key2]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Fail[agent1,key=key2]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key11]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key5]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key1]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key10]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key4]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key7]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key9]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	5f27815b-c32d-44f2-889f-72e22f4da469	test::Resource[agent1,key=key3]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	31114351-07c4-44cd-be09-aca18c10eca6	test::Resource[agent1,key=key1]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	0872a871-9858-488d-81e1-5daaa6161097	test::Resource[agent1,key=key3]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	3cddd305-42e5-404b-95c0-213bb5e31a8f	test::Resource[agent1,key=key7]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	71c693bf-d892-428f-9a95-5e11b6453cfd	test::Resource[agent1,key=key11]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	2155e7d7-164e-450b-872f-377c122d518d	test::Resource[agent1,key=key9]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	91187b9f-50c7-40fb-b866-b76712f812ae	test::Resource[agent1,key=key10]	2
a0039d95-cc53-4786-9d02-ed2485d51e3e	eee2cd59-223d-4273-819c-0319bfca9058	test::Resource[agent1,key=key5]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	556a27b3-adfc-425e-b536-cb1e50722cee	test::Resource[agent1,key=key6]	1
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key8]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key5]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key4]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key1]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key3]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Resource[agent1,key=key7]	3
a0039d95-cc53-4786-9d02-ed2485d51e3e	0320bc4b-7dd7-4106-9e6b-f5740c2f6ddf	test::Fail[agent1,key=key2]	3
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
c70de86e-2526-4c81-a1e7-38e1840e5778	1
5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	8
a0039d95-cc53-4786-9d02-ed2485d51e3e	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
NOSdrive	5fb471d9-9c94-4a11-9bf5-c014a2cfd6e2	2026-10-15 15:24:32.297598+00	\N	397a86fb-2e0b-4a6a-9fcc-f1702f7ed996
NOSdrive	c70de86e-2526-4c81-a1e7-38e1840e5778	2026-10-15 15:24:32.444685+00	\N	741d457a-f2f6-47f4-8bcd-0b4429a390ff
NOSdrive	a0039d95-cc53-4786-9d02-ed2485d51e3e	2026-10-15 15:24:54.520631+00	2026-10-15 15:24:55.312821+00	27ad7552-f416-4634-a3c7-649d221b07c0
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610150}
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

--\unrestrict qZTTEgwwya86F6UNHuCv5e8T3H8YoiLobV5Rshv5DuH0QDVSg4Tyc6aGHphID1a

