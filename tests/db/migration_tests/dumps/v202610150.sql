--
-- PostgreSQL database dump
--

--\restrict PCL2LIHaxuGCPwy84beg8Qgy6i7f5zAfSbKJ6TmRo4NH16hfd5cygjdbonzVVCl

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
    filter_metadata jsonb
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
5f92588c-2835-45b5-aa33-16f5222a6108	$__scheduler	f	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	$__scheduler	f	\N
7c10fb13-6cb7-4232-8f85-43084c1c0e4e	$__scheduler	f	\N
5f92588c-2835-45b5-aa33-16f5222a6108	localhost	f	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	localhost	f	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	internal	f	\N
5f92588c-2835-45b5-aa33-16f5222a6108	agent3	f	\N
5f92588c-2835-45b5-aa33-16f5222a6108	agent2	f	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	agent1	t	t
94cb8769-ba8a-4f2f-97be-2443965b9ef2	$__scheduler	t	t
27174925-7932-4e3d-9238-f7662755c393	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
1	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
1	internal	std	7319d4f1-651b-4a65-82fb-26e4ae099a19
1	localhost	fs	7319d4f1-651b-4a65-82fb-26e4ae099a19
2	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
2	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
3	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
3	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
4	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
4	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
5	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
5	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
6	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
6	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
7	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
7	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
8	localhost	fs	5f92588c-2835-45b5-aa33-16f5222a6108
8	localhost	std	5f92588c-2835-45b5-aa33-16f5222a6108
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
6da53480-41e8-414f-b0d9-fd5b7188b921	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:50:56.414211+00	2026-10-15 10:51:03.252716+00	2026-10-15 10:50:56.38146+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	73c33e4a-6748-4e56-83a5-9538f9a4bd0b	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6791b73b-95f0-4ef2-9332-0236ed8ed97a	7319d4f1-651b-4a65-82fb-26e4ae099a19	2026-10-15 10:51:03.52923+00	2026-10-15 10:51:08.242921+00	2026-10-15 10:51:03.505017+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	c9cdbd2c-a4a3-4fff-bf91-f78c475262c4	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6650b8d1-4e4a-49f7-bc8f-0e7cb779fb5d	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:08.46297+00	2026-10-15 10:51:09.589447+00	2026-10-15 10:51:08.44462+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	d8f5cff0-da4a-4731-a7a0-1b14bd91ffed	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f15b94ab-c214-49b1-8f46-51bddf3b6a27	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:09.695422+00	2026-10-15 10:51:10.762191+00	2026-10-15 10:51:09.651739+00	{}	{"add_one_resource": "true"}	t	f	t	3	334fff67-3174-4e70-ae82-c5dcc8fc2300	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
48f9e0e3-6215-4e4c-b782-5f34e6327639	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:11.074066+00	2026-10-15 10:51:12.136751+00	2026-10-15 10:51:11.054808+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	d8ca52ed-cb50-4cf8-abac-66f7d9ac64b8	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f4070587-b968-4492-be15-4e544165b920	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:12.378269+00	2026-10-15 10:51:13.454525+00	2026-10-15 10:51:12.362012+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	565a46dc-7624-4785-96dc-693285cc0e56	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c7284817-feea-4091-b3da-e66e3fc3aa74	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:13.596614+00	2026-10-15 10:51:17.732464+00	2026-10-15 10:51:13.583837+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	2c25d720-6318-4b35-afbc-75941259df1e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
adf5a4bf-dcab-40be-9e77-280818d6d97b	27174925-7932-4e3d-9238-f7662755c393	2026-10-15 10:51:19.11631+00	2026-10-15 10:51:19.16157+00	2026-10-15 10:51:19.064232+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	f84a40b2-db7c-49a9-88b0-d8207f1147de	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:03.194599+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2026-10-15 10:51:18.309496+00	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
1	7319d4f1-651b-4a65-82fb-26e4ae099a19	2026-10-15 10:51:08.182274+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:09.534659+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:10.706485+00	t	{"export_metadata": {"type": "manual", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:12.083195+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:13.395692+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:17.684914+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
2	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2026-10-15 10:51:18.510269+00	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:17.872379+00	t	\N	3	{}	{}	6	t	\N	\N
8	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:51:18.069955+00	t	\N	2	{}	{}	7	t	\N	\N
3	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2026-10-15 10:51:18.851684+00	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	1	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	1	fs	1.2.0
7319d4f1-651b-4a65-82fb-26e4ae099a19	1	std	7.0.0
7319d4f1-651b-4a65-82fb-26e4ae099a19	1	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	2	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	2	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	3	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	3	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	4	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	4	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	5	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	5	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	6	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	6	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	7	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	7	std	8.7.5
5f92588c-2835-45b5-aa33-16f5222a6108	8	fs	1.2.0
5f92588c-2835-45b5-aa33-16f5222a6108	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	discovery::Discovered[myagent,name=discovered]	{}	2026-10-15 10:51:18.888328+00	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
5f92588c-2835-45b5-aa33-16f5222a6108	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-15 10:51:18.888385+00	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, filter_metadata) FROM stdin;
67dc5cbe-151f-4129-991a-6888223af623	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	2026-10-15 10:51:18.451784+00	6	0	{"2b5dcfc6-8aa6-5dab-b33e-07469d4bc472": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "6b5bdb1d-7b71-57c2-9d56-c6480cf06f3f": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "8116096b-a170-5951-a638-7007da47db0f": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "9919cdf7-baf1-58b2-b1e1-d06687f582a5": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "c82df8b6-b738-593d-a649-354bbaff47e0": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "fca0c1ce-67a1-5285-a6bf-cbcf83dcf9ea": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
27174925-7932-4e3d-9238-f7662755c393	dev-4	0e6f839d-7694-448c-9eb0-c46ff178c2db			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
5f92588c-2835-45b5-aa33-16f5222a6108	dev-1	0e6f839d-7694-448c-9eb0-c46ff178c2db			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
7319d4f1-651b-4a65-82fb-26e4ae099a19	dev-1-twin	0e6f839d-7694-448c-9eb0-c46ff178c2db			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
7c10fb13-6cb7-4232-8f85-43084c1c0e4e	dev-2	0e6f839d-7694-448c-9eb0-c46ff178c2db			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
94cb8769-ba8a-4f2f-97be-2443965b9ef2	dev-3	0e6f839d-7694-448c-9eb0-c46ff178c2db			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	5f92588c-2835-45b5-aa33-16f5222a6108	\N	f
fs	1.2.0	5f92588c-2835-45b5-aa33-16f5222a6108	\N	f
std	7.0.0	7319d4f1-651b-4a65-82fb-26e4ae099a19	\N	f
fs	1.2.0	7319d4f1-651b-4a65-82fb-26e4ae099a19	\N	f
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
dfc4ea18-3ded-4778-b610-731c6891f833	27174925-7932-4e3d-9238-f7662755c393	2026-10-15 10:51:19.17313+00	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/adf5a4bf-dcab-40be-9e77-280818d6d97b	f	f	adf5a4bf-dcab-40be-9e77-280818d6d97b
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
ad5683c5-22f6-42ba-b13e-37741d46e998	fact1	value1	5f92588c-2835-45b5-aa33-16f5222a6108	std::testing::NullResource[localhost,name=test1]	fact	2026-10-15 10:51:12.282646+00	{}	f
ef6b4dba-3bfe-439e-b3f5-1c8d818ec359	fact2	value2	5f92588c-2835-45b5-aa33-16f5222a6108	std::testing::NullResource[localhost,name=test2]	fact	2026-10-15 10:51:12.300511+00	{}	t
7502f9f1-a628-472e-8141-8af0d6b09cee	fact3	value3	5f92588c-2835-45b5-aa33-16f5222a6108	std::testing::NullResource[localhost,name=test3]	fact	2026-10-15 10:51:12.314276+00	{}	t
dadc831b-40f3-4843-b69e-d2c3a2c65a79	parameter1	value1	5f92588c-2835-45b5-aa33-16f5222a6108		fact	2026-10-15 10:51:12.326954+00	{}	f
54b32e0c-b472-4321-b540-8d09feaa33d5	parameter2	value2	5f92588c-2835-45b5-aa33-16f5222a6108		fact	2026-10-15 10:51:12.33898+00	{}	f
03223e01-02a3-4cd8-9d2b-76c042490295	parameter3	value3	5f92588c-2835-45b5-aa33-16f5222a6108		fact	2026-10-15 10:51:12.35122+00	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
0e6f839d-7694-448c-9eb0-c46ff178c2db	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
3aa34147-a9f5-4ec6-9476-0245e1715dd8	2026-10-15 10:50:56.421527+00	2026-10-15 10:50:56.443104+00		Init		Using extra environment variables during compile \n	0	6da53480-41e8-414f-b0d9-fd5b7188b921
ee7740b8-936f-4879-b134-2c3efe1aeaaf	2026-10-15 10:50:56.451947+00	2026-10-15 10:50:56.47402+00		Venv check		Creating new venv at /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env-py3.14\n	0	6da53480-41e8-414f-b0d9-fd5b7188b921
ca2a929e-a0e2-426b-af97-01718a957c5f	2026-10-15 10:50:56.486362+00	2026-10-15 10:50:56.83058+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6da53480-41e8-414f-b0d9-fd5b7188b921
130c182c-1224-4e21-ac60-c6dd4e5481c1	2026-10-15 10:51:03.604237+00	2026-10-15 10:51:03.838074+00	/tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6791b73b-95f0-4ef2-9332-0236ed8ed97a
4cbe5235-9cea-414d-b88b-42ec602a8fc8	2026-10-15 10:50:56.838693+00	2026-10-15 10:51:02.234935+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpegnbyu_7:\n                                 Pip command: /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpegnbyu_7 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Downloading more_itertools-11.2.1-py3-none-any.whl.metadata (42 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl.metadata (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Downloading pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.334.4)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Downloading strawberry_graphql-0.335.0-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Downloading more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Downloading pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.2/2.2 MB 22.5 MB/s  0:00:00\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Downloading strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Downloading mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: pydantic-core, more-itertools, mitogen, strawberry-graphql, pydantic, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.2.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.334.4\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.54 more-itertools-11.2.1 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.335.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	6da53480-41e8-414f-b0d9-fd5b7188b921
884b66d0-afc3-45a0-ad2f-520b38aaf25c	2026-10-15 10:51:02.243065+00	2026-10-15 10:51:03.244127+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp8v7it6y9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.017 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.037 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.073 seconds\ncompiler       DEBUG   The entire export command took 0.150 seconds\n	0	6da53480-41e8-414f-b0d9-fd5b7188b921
d11a3f86-175b-4049-b160-3e34ed276680	2026-10-15 10:51:03.53684+00	2026-10-15 10:51:03.562314+00		Init		Using extra environment variables during compile \n	0	6791b73b-95f0-4ef2-9332-0236ed8ed97a
c8892a01-1eff-4a8f-a95b-020d2007ef83	2026-10-15 10:51:03.570952+00	2026-10-15 10:51:03.591305+00		Venv check		Creating new venv at /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env-py3.14\n	0	6791b73b-95f0-4ef2-9332-0236ed8ed97a
88d1b809-4643-4979-bc81-e8da889072e3	2026-10-15 10:51:07.257141+00	2026-10-15 10:51:08.234997+00	/tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7319d4f1-651b-4a65-82fb-26e4ae099a19 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmplh6u8tj3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.008 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.026 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.055 seconds\ncompiler       DEBUG   The entire export command took 0.112 seconds\n	0	6791b73b-95f0-4ef2-9332-0236ed8ed97a
7445df96-349a-4839-a589-131d76408eda	2026-10-15 10:51:08.471077+00	2026-10-15 10:51:08.493158+00		Init		Using extra environment variables during compile \n	0	6650b8d1-4e4a-49f7-bc8f-0e7cb779fb5d
cba755c3-4494-41d8-bb27-2ab2bce6ee37	2026-10-15 10:51:08.501392+00	2026-10-15 10:51:08.518168+00		Venv check		Found existing venv\n	0	6650b8d1-4e4a-49f7-bc8f-0e7cb779fb5d
702136d8-07fe-479c-9a70-8084c41a0480	2026-10-15 10:51:03.845304+00	2026-10-15 10:51:07.249471+00	/tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp5oqogaqe:\n                                 Pip command: /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp5oqogaqe inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl.metadata (42 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.13.5)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl.metadata (133 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.1 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl.metadata (6.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.334.4)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.1-py3-none-any.whl (488 kB)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.1-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (2.2 MB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: pydantic-core, more-itertools, mitogen, strawberry-graphql, pydantic, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.46.5\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.2.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.334.4\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.13.5\ninmanta.pip              DEBUG   Not uninstalling pydantic at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/7319d4f1-651b-4a65-82fb-26e4ae099a19/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.54 more-itertools-11.2.1 pydantic-2.14.1 pydantic-core-2.50.1 strawberry-graphql-0.335.0\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	6791b73b-95f0-4ef2-9332-0236ed8ed97a
3a034ab5-a1f6-4ff2-8a31-e963498393f5	2026-10-15 10:51:09.73289+00	2026-10-15 10:51:09.749783+00		Venv check		Found existing venv\n	0	f15b94ab-c214-49b1-8f46-51bddf3b6a27
c02adf49-674f-4556-a2d2-654dbc213c66	2026-10-15 10:51:16.730679+00	2026-10-15 10:51:17.724975+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmprcfm_d6g --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.040 seconds\ncompiler       DEBUG   The entire export command took 0.108 seconds\n	0	c7284817-feea-4091-b3da-e66e3fc3aa74
9f929fe5-21ea-4a8d-bf24-df626eff2e9e	2026-10-15 10:51:11.139438+00	2026-10-15 10:51:12.129268+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpwnjhd_jo --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.042 seconds\ncompiler       DEBUG   The entire export command took 0.111 seconds\n	0	48f9e0e3-6215-4e4c-b782-5f34e6327639
d6689863-df0e-425c-9067-400fa4af75b6	2026-10-15 10:51:13.66598+00	2026-10-15 10:51:13.889009+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	c7284817-feea-4091-b3da-e66e3fc3aa74
6b92c1b8-866f-4a89-943e-36fe44461171	2026-10-15 10:51:12.38597+00	2026-10-15 10:51:12.402883+00		Init		Using extra environment variables during compile \n	0	f4070587-b968-4492-be15-4e544165b920
0efc591d-a5eb-4abb-a00f-56fcddd8f0c8	2026-10-15 10:51:09.758474+00	2026-10-15 10:51:10.753382+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmph_y70tvi --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.035 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.058 seconds\ncompiler       DEBUG   The entire export command took 0.124 seconds\n	0	f15b94ab-c214-49b1-8f46-51bddf3b6a27
cab7ba66-d56e-4196-bc02-4000e9aa4cfe	2026-10-15 10:51:08.525959+00	2026-10-15 10:51:09.580918+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpgv74e83o --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.110 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.032 seconds\ncompiler       DEBUG   The entire export command took 0.175 seconds\n	0	6650b8d1-4e4a-49f7-bc8f-0e7cb779fb5d
e9c58d4e-c750-4da4-a518-4beb64f33e6d	2026-10-15 10:51:09.704002+00	2026-10-15 10:51:09.724708+00		Init		Using extra environment variables during compile add_one_resource='true'\n	0	f15b94ab-c214-49b1-8f46-51bddf3b6a27
a8af7fc6-c33b-4c75-b0c7-2957c08e881b	2026-10-15 10:51:12.435695+00	2026-10-15 10:51:13.445074+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 5f92588c-2835-45b5-aa33-16f5222a6108 --server_address localhost --server_port 44197 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp21nzdu3f --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.031 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:44197/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:44197/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.044 seconds\ncompiler       DEBUG   The entire export command took 0.110 seconds\n	0	f4070587-b968-4492-be15-4e544165b920
b5fe64b4-b4fe-4532-9cf2-62797caac1f5	2026-10-15 10:51:11.082539+00	2026-10-15 10:51:11.105696+00		Init		Using extra environment variables during compile \n	0	48f9e0e3-6215-4e4c-b782-5f34e6327639
1985a80a-847b-4156-b3ca-e8d6c857f851	2026-10-15 10:51:11.114005+00	2026-10-15 10:51:11.131914+00		Venv check		Found existing venv\n	0	48f9e0e3-6215-4e4c-b782-5f34e6327639
20526de0-13d3-491d-ba3d-cf089a7dbc29	2026-10-15 10:51:12.41036+00	2026-10-15 10:51:12.427008+00		Venv check		Found existing venv\n	0	f4070587-b968-4492-be15-4e544165b920
4ccf6780-3fce-4be9-ab77-d9ae14a95213	2026-10-15 10:51:13.603872+00	2026-10-15 10:51:13.627609+00		Init		Using extra environment variables during compile \n	0	c7284817-feea-4091-b3da-e66e3fc3aa74
ae3417f0-aaa0-4f6c-a5fb-376c6ca5823a	2026-10-15 10:51:19.125133+00	2026-10-15 10:51:19.153789+00		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpe0plce44/server/27174925-7932-4e3d-9238-f7662755c393/compiler and no repository set.\n	1	adf5a4bf-dcab-40be-9e77-280818d6d97b
1b41c970-a654-420f-a279-f3edeb897255	2026-10-15 10:51:13.63626+00	2026-10-15 10:51:13.654346+00		Venv check		Found existing venv\n	0	c7284817-feea-4091-b3da-e66e3fc3aa74
b9234c73-bea7-4d89-ba68-3b60279067bb	2026-10-15 10:51:13.897778+00	2026-10-15 10:51:16.722377+00	/tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpeegv54de:\n                                 Pip command: /tmp/tmpe0plce44/server/5f92588c-2835-45b5-aa33-16f5222a6108/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpeegv54de inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in ./.env/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in ./.env/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.335.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /tmp/claude-1000/-home-jp-Inmanta/2e441860-eea4-4191-ac65-1e8950bc6522/scratchpad/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	c7284817-feea-4091-b3da-e66e3fc3aa74
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	18048b59-f0ff-43c1-9485-015ff93ac77c
7319d4f1-651b-4a65-82fb-26e4ae099a19	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	3fa01d21-52d0-4ff5-afc6-fe8cb2d7da25
7319d4f1-651b-4a65-82fb-26e4ae099a19	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3fa01d21-52d0-4ff5-afc6-fe8cb2d7da25
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6ef2eb5e-3125-4fdc-9394-f9a26b2131d5
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	401876e7-2c13-4e48-8057-b673eab48a04
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	401876e7-2c13-4e48-8057-b673eab48a04
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d23474cf-418b-4e3e-9253-7fdadb6a450c
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	80a5d9e4-1807-49da-90ba-6aeba609ad06
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	1c635aeb-8113-47ee-b835-2e416e240886
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7ea2fe62-9438-4abd-9912-83d55b74081a
5f92588c-2835-45b5-aa33-16f5222a6108	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	50a943af-aa39-49b4-ba9a-63ef9e216ceb
5f92588c-2835-45b5-aa33-16f5222a6108	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	ca49f172-a0f4-4e6e-a2d2-5f2a75971618
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ce454355-b157-48c0-825e-45e6bcb627b3
5f92588c-2835-45b5-aa33-16f5222a6108	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	538298d6-0082-4758-8b4a-2288a049ede1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
a260e3b6-902c-4c5e-a103-659c7c32b5bc	94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-15 10:51:18.659765+00
f4de8d71-f618-4ae5-8d5c-ef37437a32e4	94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-15 10:51:18.713973+00
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-15 10:51:18.321726+00	\N	\N	\N
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test]	2026-10-15 10:51:03.404865+00	\N	2026-10-15 10:51:03.404865+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:03.366826+00	f	\N	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Fail[agent1,key=key2]	2026-10-15 10:51:18.356393+00	\N	2026-10-15 10:51:18.356393+00	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:18.321726+00	f	\N	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key11]	2026-10-15 10:51:18.659765+00	\N	2026-10-15 10:51:18.659765+00	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.534018+00	f	a260e3b6-902c-4c5e-a103-659c7c32b5bc	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key3]	2026-10-15 10:51:18.375055+00	\N	2026-10-15 10:51:18.375055+00	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-15 10:51:18.321726+00	f	\N	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	std::AgentConfig[internal,agentname=localhost]	2026-10-15 10:51:08.330016+00	\N	2026-10-15 10:51:08.330016+00	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:08.291696+00	f	\N	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	fs::File[localhost,path=/tmp/test]	2026-10-15 10:51:08.357826+00	\N	2026-10-15 10:51:08.357826+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:08.291696+00	f	\N	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key9]	2026-10-15 10:51:18.690143+00	2026-10-15 10:51:18.671067+00	2026-10-15 10:51:18.690143+00	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.534018+00	t	\N	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key1]	2026-10-15 10:51:18.418499+00	2026-10-15 10:51:18.40536+00	2026-10-15 10:51:18.418499+00	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.321726+00	t	\N	\N
5f92588c-2835-45b5-aa33-16f5222a6108	fs::File[localhost,path=/tmp/test_orphan]	2026-10-15 10:51:10.943203+00	\N	2026-10-15 10:51:10.943203+00	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:10.904828+00	f	\N	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key10]	2026-10-15 10:51:18.713973+00	\N	2026-10-15 10:51:18.713973+00	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.534018+00	f	f4de8d71-f618-4ae5-8d5c-ef37437a32e4	\N
5f92588c-2835-45b5-aa33-16f5222a6108	test::Resource[agent2,key=key2]	2026-10-15 10:51:17.949679+00	\N	2026-10-15 10:51:17.949679+00	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:17.920825+00	f	\N	\N
5f92588c-2835-45b5-aa33-16f5222a6108	test::Resource[agent3,key=key3]	2026-10-15 10:51:17.963295+00	\N	2026-10-15 10:51:17.963295+00	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-15 10:51:17.920825+00	f	\N	7
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-15 10:51:18.321726+00	\N	\N	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key6]	2026-10-15 10:51:18.397159+00	2026-10-15 10:51:18.383302+00	2026-10-15 10:51:18.397159+00	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.321726+00	t	\N	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	test::Resource[agent1,key=key7]	2026-10-15 10:51:18.627444+00	2026-10-15 10:51:18.588624+00	2026-10-15 10:51:18.627444+00	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-15 10:51:18.534018+00	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	18048b59-f0ff-43c1-9485-015ff93ac77c	\N
7319d4f1-651b-4a65-82fb-26e4ae099a19	3fa01d21-52d0-4ff5-afc6-fe8cb2d7da25	\N
5f92588c-2835-45b5-aa33-16f5222a6108	6ef2eb5e-3125-4fdc-9394-f9a26b2131d5	\N
5f92588c-2835-45b5-aa33-16f5222a6108	401876e7-2c13-4e48-8057-b673eab48a04	\N
5f92588c-2835-45b5-aa33-16f5222a6108	d23474cf-418b-4e3e-9253-7fdadb6a450c	\N
5f92588c-2835-45b5-aa33-16f5222a6108	80a5d9e4-1807-49da-90ba-6aeba609ad06	\N
5f92588c-2835-45b5-aa33-16f5222a6108	1c635aeb-8113-47ee-b835-2e416e240886	\N
5f92588c-2835-45b5-aa33-16f5222a6108	7ea2fe62-9438-4abd-9912-83d55b74081a	\N
5f92588c-2835-45b5-aa33-16f5222a6108	50a943af-aa39-49b4-ba9a-63ef9e216ceb	set-b
5f92588c-2835-45b5-aa33-16f5222a6108	ca49f172-a0f4-4e6e-a2d2-5f2a75971618	set-a
5f92588c-2835-45b5-aa33-16f5222a6108	ce454355-b157-48c0-825e-45e6bcb627b3	\N
5f92588c-2835-45b5-aa33-16f5222a6108	538298d6-0082-4758-8b4a-2288a049ede1	set-a
94cb8769-ba8a-4f2f-97be-2443965b9ef2	37560ef7-98d0-4e78-9987-1cb2cd67fdad	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	984ab5b4-dc76-41a8-91e9-b7de65b2f45e	\N
94cb8769-ba8a-4f2f-97be-2443965b9ef2	2bdc7c8f-e303-401e-90e0-ca6dff9ac436	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	1	18048b59-f0ff-43c1-9485-015ff93ac77c
7319d4f1-651b-4a65-82fb-26e4ae099a19	1	3fa01d21-52d0-4ff5-afc6-fe8cb2d7da25
5f92588c-2835-45b5-aa33-16f5222a6108	2	6ef2eb5e-3125-4fdc-9394-f9a26b2131d5
5f92588c-2835-45b5-aa33-16f5222a6108	3	401876e7-2c13-4e48-8057-b673eab48a04
5f92588c-2835-45b5-aa33-16f5222a6108	4	d23474cf-418b-4e3e-9253-7fdadb6a450c
5f92588c-2835-45b5-aa33-16f5222a6108	5	80a5d9e4-1807-49da-90ba-6aeba609ad06
5f92588c-2835-45b5-aa33-16f5222a6108	6	1c635aeb-8113-47ee-b835-2e416e240886
5f92588c-2835-45b5-aa33-16f5222a6108	7	7ea2fe62-9438-4abd-9912-83d55b74081a
5f92588c-2835-45b5-aa33-16f5222a6108	7	50a943af-aa39-49b4-ba9a-63ef9e216ceb
5f92588c-2835-45b5-aa33-16f5222a6108	7	ca49f172-a0f4-4e6e-a2d2-5f2a75971618
5f92588c-2835-45b5-aa33-16f5222a6108	8	ce454355-b157-48c0-825e-45e6bcb627b3
5f92588c-2835-45b5-aa33-16f5222a6108	8	538298d6-0082-4758-8b4a-2288a049ede1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	37560ef7-98d0-4e78-9987-1cb2cd67fdad
94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	984ab5b4-dc76-41a8-91e9-b7de65b2f45e
94cb8769-ba8a-4f2f-97be-2443965b9ef2	3	2bdc7c8f-e303-401e-90e0-ca6dff9ac436
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
7030c090-1159-4367-ab25-25c6f4bb1be7	store	2026-10-15 10:51:03.19416+00	2026-10-15 10:51:03.207732+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T11:51:03.207748+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	1	{"fs::File[localhost,path=/tmp/test],v=1"}
eef90966-bd7d-4da4-9b0f-0986b7223e6c	deploy	2026-10-15 10:51:03.389335+00	2026-10-15 10:51:03.404865+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:03.404049+01:00\\"}"}	unavailable	\N	nochange	5f92588c-2835-45b5-aa33-16f5222a6108	1	{"fs::File[localhost,path=/tmp/test],v=1"}
e39987bd-3a19-4e62-a8ce-aba625620d85	store	2026-10-15 10:51:08.181912+00	2026-10-15 10:51:08.197458+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T11:51:08.197474+01:00\\"}"}	\N	\N	\N	7319d4f1-651b-4a65-82fb-26e4ae099a19	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
55b552fb-e154-4279-a8fc-2e28f67b35fe	deploy	2026-10-15 10:51:08.31526+00	2026-10-15 10:51:08.330016+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:08.329150+01:00\\"}"}	unavailable	\N	nochange	7319d4f1-651b-4a65-82fb-26e4ae099a19	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
f0b657b5-746c-4ce9-af5f-568223ad8a08	deploy	2026-10-15 10:51:08.346908+00	2026-10-15 10:51:08.357826+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:08.356237+01:00\\"}"}	unavailable	\N	nochange	7319d4f1-651b-4a65-82fb-26e4ae099a19	1	{"fs::File[localhost,path=/tmp/test],v=1"}
6ce50164-47e1-4ffe-b458-764ba4f3619e	store	2026-10-15 10:51:09.534498+00	2026-10-15 10:51:09.540557+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-15T11:51:09.540584+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	2	{"fs::File[localhost,path=/tmp/test],v=2"}
e5cf5100-f786-46a0-a87e-e8d5b8faf699	store	2026-10-15 10:51:10.706325+00	2026-10-15 10:51:10.710892+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-15T11:51:10.710904+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
f332b6d7-3a6c-4236-97e6-b8c1d0ea284b	deploy	2026-10-15 10:51:10.924039+00	2026-10-15 10:51:10.943203+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-15T11:51:10.941543+01:00\\"}"}	unavailable	\N	nochange	5f92588c-2835-45b5-aa33-16f5222a6108	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
5d3d69c7-63ad-4eab-827c-288161349d67	store	2026-10-15 10:51:12.082916+00	2026-10-15 10:51:12.089782+00	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-15T11:51:12.089815+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	4	{"fs::File[localhost,path=/tmp/test],v=4"}
880b01d9-2b44-43b5-9a08-6f58517eb963	store	2026-10-15 10:51:13.395569+00	2026-10-15 10:51:13.401983+00	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-15T11:51:13.402010+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	5	{"fs::File[localhost,path=/tmp/test],v=5"}
b54cd48b-6565-487f-a19f-c75b2d259b68	store	2026-10-15 10:51:17.684522+00	2026-10-15 10:51:17.692101+00	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-15T11:51:17.692120+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	6	{"fs::File[localhost,path=/tmp/test],v=6"}
34106621-14e5-481f-92a7-8eda75ff9222	store	2026-10-15 10:51:17.87223+00	2026-10-15 10:51:17.882382+00	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-15T11:51:17.882393+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	7	{"test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7"}
1caa8a47-a8e8-4934-8390-19a054aee85a	deploy	2026-10-15 10:51:17.949921+00	2026-10-15 10:51:17.963295+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-15T11:51:17.961698+01:00\\"}"}	unavailable	\N	nochange	5f92588c-2835-45b5-aa33-16f5222a6108	7	{"test::Resource[agent3,key=key3],v=7"}
adf6fe8b-e74d-49a5-9150-c8b18457926e	deploy	2026-10-15 10:51:17.934417+00	2026-10-15 10:51:17.949679+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-15T11:51:17.947747+01:00\\"}"}	unavailable	\N	nochange	5f92588c-2835-45b5-aa33-16f5222a6108	7	{"test::Resource[agent2,key=key2],v=7"}
9fd8ac29-b242-4896-b4da-1710a6e91fe3	store	2026-10-15 10:51:18.069685+00	2026-10-15 10:51:18.081031+00	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-15T11:51:18.081052+01:00\\"}"}	\N	\N	\N	5f92588c-2835-45b5-aa33-16f5222a6108	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
843b3154-63a6-4223-987f-9bff5800c972	store	2026-10-15 10:51:18.309426+00	2026-10-15 10:51:18.312369+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-15T11:51:18.312378+01:00\\"}"}	\N	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key3],v=1"}
e7c09160-d0a3-428c-88dd-4e97a22861a6	deploy	2026-10-15 10:51:18.340402+00	2026-10-15 10:51:18.356393+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 66c7e370-8d45-4209-bdd1-5ddd71f95c7f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"66c7e370-8d45-4209-bdd1-5ddd71f95c7f\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.354182+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/jp/Inmanta/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.355524+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 66c7e370-8d45-4209-bdd1-5ddd71f95c7f) - duration: 0.0020 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0020499229431152344, \\"deploy_id\\": \\"66c7e370-8d45-4209-bdd1-5ddd71f95c7f\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.356337+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Fail[agent1,key=key2],v=1"}
df858cb0-9b06-464c-9fd5-b0c4e57d7272	deploy	2026-10-15 10:51:18.366051+00	2026-10-15 10:51:18.375055+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: eda8309c-aa77-40aa-9aec-7047e614f22a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"eda8309c-aa77-40aa-9aec-7047e614f22a\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.374676+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.374850+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: eda8309c-aa77-40aa-9aec-7047e614f22a) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00024700164794921875, \\"deploy_id\\": \\"eda8309c-aa77-40aa-9aec-7047e614f22a\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.375009+01:00\\"}"}	skipped	\N	nochange	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key3],v=1"}
478facb8-8486-4177-9604-4d92c50b7942	deploy	2026-10-15 10:51:18.383358+00	2026-10-15 10:51:18.397159+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 91d9fb4b-2092-45e0-8e4a-5b52a85f5436).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"91d9fb4b-2092-45e0-8e4a-5b52a85f5436\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.391172+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 91d9fb4b-2092-45e0-8e4a-5b52a85f5436) - duration: 0.0058 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.005847454071044922, \\"deploy_id\\": \\"91d9fb4b-2092-45e0-8e4a-5b52a85f5436\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.397106+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key6],v=1"}
c202f775-ee89-4528-b46f-5dd8b0b0a0be	deploy	2026-10-15 10:51:18.405417+00	2026-10-15 10:51:18.418499+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 863e181d-d475-43da-aef7-104997805c43).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"863e181d-d475-43da-aef7-104997805c43\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.413184+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 863e181d-d475-43da-aef7-104997805c43) - duration: 0.0052 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.005181074142456055, \\"deploy_id\\": \\"863e181d-d475-43da-aef7-104997805c43\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.418448+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key1],v=1"}
cf6a1484-337b-48e7-9837-e7c767474b07	dryrun	2026-10-15 10:51:18.463374+00	2026-10-15 10:51:18.463958+00	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.463468+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003485679626464844, \\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.463927+01:00\\"}"}	dry	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Fail[agent1,key=key2],v=1"}
38ccb5d8-0dff-4877-9a94-312c541332e3	dryrun	2026-10-15 10:51:18.507197+00	2026-10-15 10:51:18.508448+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.507347+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623 - duration 0.0009 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.000919342041015625, \\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.508399+01:00\\"}"}	dry	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key1],v=1"}
5b4dc8e0-6228-4948-acb7-6ec46f6adfea	store	2026-10-15 10:51:18.509282+00	2026-10-15 10:51:18.51574+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-15T11:51:18.515763+01:00\\"}"}	\N	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	{"test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key1],v=2"}
a878dabf-9f02-458f-8a07-f40b0dde4391	store	2026-10-15 10:51:18.85153+00	2026-10-15 10:51:18.859303+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-15T11:51:18.859336+01:00\\"}"}	\N	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	3	{"test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key5],v=3"}
53787788-bae2-4d3e-8582-3b912b28ffe5	dryrun	2026-10-15 10:51:18.53246+00	2026-10-15 10:51:18.533299+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.532594+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623 - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005395412445068359, \\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.533254+01:00\\"}"}	dry	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key3],v=1"}
81c07ca5-1cef-4671-ad3e-b61ca2b190bf	dryrun	2026-10-15 10:51:18.558409+00	2026-10-15 10:51:18.559421+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.558590+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623 - duration 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006611347198486328, \\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.559380+01:00\\"}"}	dry	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key5],v=1"}
7543fd1f-d0eb-49ed-b7fc-ec7ddfc4a6d6	deploy	2026-10-15 10:51:18.588788+00	2026-10-15 10:51:18.627444+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: f1ad5304-7f6e-4313-ac4a-bcb0009b876a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"f1ad5304-7f6e-4313-ac4a-bcb0009b876a\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.606262+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: f1ad5304-7f6e-4313-ac4a-bcb0009b876a) - duration: 0.0209 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.02093338966369629, \\"deploy_id\\": \\"f1ad5304-7f6e-4313-ac4a-bcb0009b876a\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.627350+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	{"test::Resource[agent1,key=key7],v=2"}
28612f33-32e4-4d24-bb2d-8302cb679209	deploy	2026-10-15 10:51:18.63788+00	2026-10-15 10:51:18.659765+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 02fb7030-110d-469f-9502-077161dea373).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"02fb7030-110d-469f-9502-077161dea373\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.647608+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.648185+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 02fb7030-110d-469f-9502-077161dea373) - duration: 0.0119 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.011946916580200195, \\"deploy_id\\": \\"02fb7030-110d-469f-9502-077161dea373\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.659687+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	{"test::Resource[agent1,key=key11],v=2"}
98b0b196-85ed-44c6-8d41-e5f9c2073a78	deploy	2026-10-15 10:51:18.671165+00	2026-10-15 10:51:18.690143+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 87618a8c-1c7b-4b28-b21e-71423c7fb28c).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"87618a8c-1c7b-4b28-b21e-71423c7fb28c\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.681413+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 87618a8c-1c7b-4b28-b21e-71423c7fb28c) - duration: 0.0086 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.008570194244384766, \\"deploy_id\\": \\"87618a8c-1c7b-4b28-b21e-71423c7fb28c\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.690078+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	{"test::Resource[agent1,key=key9],v=2"}
172bce6a-ed59-4b8e-8cb5-bd547423f822	deploy	2026-10-15 10:51:18.698739+00	2026-10-15 10:51:18.713973+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ef7ff816-4f22-46bd-8a68-0763949361a9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"ef7ff816-4f22-46bd-8a68-0763949361a9\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.707377+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.707651+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: ef7ff816-4f22-46bd-8a68-0763949361a9) - duration: 0.0064 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0064411163330078125, \\"deploy_id\\": \\"ef7ff816-4f22-46bd-8a68-0763949361a9\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.713910+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2	{"test::Resource[agent1,key=key10],v=2"}
08a511ac-20ab-4016-af3a-4fa1c01692ee	dryrun	2026-10-15 10:51:18.723441+00	2026-10-15 10:51:18.724117+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.723572+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 67dc5cbe-151f-4129-991a-6888223af623 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0004229545593261719, \\"dry_run_id\\": \\"67dc5cbe-151f-4129-991a-6888223af623\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-15T11:51:18.724087+01:00\\"}"}	dry	\N	\N	94cb8769-ba8a-4f2f-97be-2443965b9ef2	1	{"test::Resource[agent1,key=key6],v=1"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
5f92588c-2835-45b5-aa33-16f5222a6108	7030c090-1159-4367-ab25-25c6f4bb1be7	fs::File[localhost,path=/tmp/test]	1
5f92588c-2835-45b5-aa33-16f5222a6108	eef90966-bd7d-4da4-9b0f-0986b7223e6c	fs::File[localhost,path=/tmp/test]	1
7319d4f1-651b-4a65-82fb-26e4ae099a19	e39987bd-3a19-4e62-a8ce-aba625620d85	fs::File[localhost,path=/tmp/test]	1
7319d4f1-651b-4a65-82fb-26e4ae099a19	e39987bd-3a19-4e62-a8ce-aba625620d85	std::AgentConfig[internal,agentname=localhost]	1
7319d4f1-651b-4a65-82fb-26e4ae099a19	55b552fb-e154-4279-a8fc-2e28f67b35fe	std::AgentConfig[internal,agentname=localhost]	1
7319d4f1-651b-4a65-82fb-26e4ae099a19	f0b657b5-746c-4ce9-af5f-568223ad8a08	fs::File[localhost,path=/tmp/test]	1
5f92588c-2835-45b5-aa33-16f5222a6108	6ce50164-47e1-4ffe-b458-764ba4f3619e	fs::File[localhost,path=/tmp/test]	2
5f92588c-2835-45b5-aa33-16f5222a6108	e5cf5100-f786-46a0-a87e-e8d5b8faf699	fs::File[localhost,path=/tmp/test]	3
5f92588c-2835-45b5-aa33-16f5222a6108	e5cf5100-f786-46a0-a87e-e8d5b8faf699	fs::File[localhost,path=/tmp/test_orphan]	3
5f92588c-2835-45b5-aa33-16f5222a6108	f332b6d7-3a6c-4236-97e6-b8c1d0ea284b	fs::File[localhost,path=/tmp/test_orphan]	3
5f92588c-2835-45b5-aa33-16f5222a6108	5d3d69c7-63ad-4eab-827c-288161349d67	fs::File[localhost,path=/tmp/test]	4
5f92588c-2835-45b5-aa33-16f5222a6108	880b01d9-2b44-43b5-9a08-6f58517eb963	fs::File[localhost,path=/tmp/test]	5
5f92588c-2835-45b5-aa33-16f5222a6108	b54cd48b-6565-487f-a19f-c75b2d259b68	fs::File[localhost,path=/tmp/test]	6
5f92588c-2835-45b5-aa33-16f5222a6108	34106621-14e5-481f-92a7-8eda75ff9222	test::Resource[agent2,key=key2]	7
5f92588c-2835-45b5-aa33-16f5222a6108	34106621-14e5-481f-92a7-8eda75ff9222	test::Resource[agent3,key=key3]	7
5f92588c-2835-45b5-aa33-16f5222a6108	34106621-14e5-481f-92a7-8eda75ff9222	fs::File[localhost,path=/tmp/test]	7
5f92588c-2835-45b5-aa33-16f5222a6108	adf6fe8b-e74d-49a5-9150-c8b18457926e	test::Resource[agent2,key=key2]	7
5f92588c-2835-45b5-aa33-16f5222a6108	1caa8a47-a8e8-4934-8390-19a054aee85a	test::Resource[agent3,key=key3]	7
5f92588c-2835-45b5-aa33-16f5222a6108	9fd8ac29-b242-4896-b4da-1710a6e91fe3	fs::File[localhost,path=/tmp/test]	8
5f92588c-2835-45b5-aa33-16f5222a6108	9fd8ac29-b242-4896-b4da-1710a6e91fe3	test::Resource[agent2,key=key2]	8
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Resource[agent1,key=key1]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Resource[agent1,key=key4]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Resource[agent1,key=key6]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Resource[agent1,key=key5]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Fail[agent1,key=key2]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	843b3154-63a6-4223-987f-9bff5800c972	test::Resource[agent1,key=key3]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	e7c09160-d0a3-428c-88dd-4e97a22861a6	test::Fail[agent1,key=key2]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	df858cb0-9b06-464c-9fd5-b0c4e57d7272	test::Resource[agent1,key=key3]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	478facb8-8486-4177-9604-4d92c50b7942	test::Resource[agent1,key=key6]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	c202f775-ee89-4528-b46f-5dd8b0b0a0be	test::Resource[agent1,key=key1]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	cf6a1484-337b-48e7-9837-e7c767474b07	test::Fail[agent1,key=key2]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key4]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key7]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Fail[agent1,key=key2]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key3]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key10]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key11]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key9]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key5]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	5b4dc8e0-6228-4948-acb7-6ec46f6adfea	test::Resource[agent1,key=key1]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	38ccb5d8-0dff-4877-9a94-312c541332e3	test::Resource[agent1,key=key1]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	53787788-bae2-4d3e-8582-3b912b28ffe5	test::Resource[agent1,key=key3]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	81c07ca5-1cef-4671-ad3e-b61ca2b190bf	test::Resource[agent1,key=key5]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	7543fd1f-d0eb-49ed-b7fc-ec7ddfc4a6d6	test::Resource[agent1,key=key7]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	28612f33-32e4-4d24-bb2d-8302cb679209	test::Resource[agent1,key=key11]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	98b0b196-85ed-44c6-8d41-e5f9c2073a78	test::Resource[agent1,key=key9]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	172bce6a-ed59-4b8e-8cb5-bd547423f822	test::Resource[agent1,key=key10]	2
94cb8769-ba8a-4f2f-97be-2443965b9ef2	08a511ac-20ab-4016-af3a-4fa1c01692ee	test::Resource[agent1,key=key6]	1
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Fail[agent1,key=key2]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key4]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key3]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key8]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key1]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key7]	3
94cb8769-ba8a-4f2f-97be-2443965b9ef2	a878dabf-9f02-458f-8a07-f40b0dde4391	test::Resource[agent1,key=key5]	3
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
7319d4f1-651b-4a65-82fb-26e4ae099a19	1
5f92588c-2835-45b5-aa33-16f5222a6108	8
94cb8769-ba8a-4f2f-97be-2443965b9ef2	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
NOSdrive	5f92588c-2835-45b5-aa33-16f5222a6108	2026-10-15 10:50:55.998037+00	\N	39cc0a75-e778-4422-bb32-7b4e7af242db
NOSdrive	7319d4f1-651b-4a65-82fb-26e4ae099a19	2026-10-15 10:50:56.154906+00	\N	a784b999-6b3a-4823-9a4b-a1ec84bf73c5
NOSdrive	94cb8769-ba8a-4f2f-97be-2443965b9ef2	2026-10-15 10:51:18.165535+00	2026-10-15 10:51:18.824456+00	04fe78eb-e554-4c6b-91ba-3f4cb4f01a07
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

--\unrestrict PCL2LIHaxuGCPwy84beg8Qgy6i7f5zAfSbKJ6TmRo4NH16hfd5cygjdbonzVVCl

