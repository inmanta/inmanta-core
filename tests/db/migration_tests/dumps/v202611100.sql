--
-- PostgreSQL database dump
--

--\restrict OhuSWprJVmRKfQwRt09C7Sa2v7RLRIrS7jgjSvbdtIwwqBrGBdWe5tqarzWU1No

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
8848d954-8550-43c8-8784-c56446578137	$__scheduler	f	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	$__scheduler	f	\N
94295a98-8135-4d1b-95b3-5c77ec84fe27	$__scheduler	f	\N
8848d954-8550-43c8-8784-c56446578137	localhost	f	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	localhost	f	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	internal	f	\N
8848d954-8550-43c8-8784-c56446578137	agent3	f	\N
8848d954-8550-43c8-8784-c56446578137	agent2	f	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	agent1	t	t
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	$__scheduler	t	t
4497d6a2-4aca-4d36-993a-0f6459475158	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	8848d954-8550-43c8-8784-c56446578137
1	localhost	fs	8848d954-8550-43c8-8784-c56446578137
1	internal	std	616dfc7b-e970-4004-b040-b33fcdb1b963
1	localhost	fs	616dfc7b-e970-4004-b040-b33fcdb1b963
2	localhost	std	8848d954-8550-43c8-8784-c56446578137
2	localhost	fs	8848d954-8550-43c8-8784-c56446578137
3	localhost	std	8848d954-8550-43c8-8784-c56446578137
3	localhost	fs	8848d954-8550-43c8-8784-c56446578137
4	localhost	std	8848d954-8550-43c8-8784-c56446578137
4	localhost	fs	8848d954-8550-43c8-8784-c56446578137
5	localhost	std	8848d954-8550-43c8-8784-c56446578137
5	localhost	fs	8848d954-8550-43c8-8784-c56446578137
6	localhost	std	8848d954-8550-43c8-8784-c56446578137
6	localhost	fs	8848d954-8550-43c8-8784-c56446578137
7	localhost	fs	8848d954-8550-43c8-8784-c56446578137
7	localhost	std	8848d954-8550-43c8-8784-c56446578137
8	localhost	fs	8848d954-8550-43c8-8784-c56446578137
8	localhost	std	8848d954-8550-43c8-8784-c56446578137
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
f032f615-0006-4cfe-9010-7cc7f775d914	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:01:52.131235+01	2026-11-13 16:02:01.464411+01	2026-11-13 16:01:52.123427+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	3278a7ba-343f-42fd-a4a3-f36f437782d4	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
9609dc26-dc6b-4cc6-a26a-fb334feaf8d5	616dfc7b-e970-4004-b040-b33fcdb1b963	2026-11-13 16:02:01.739778+01	2026-11-13 16:02:10.329534+01	2026-11-13 16:02:01.726977+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	062c1a94-df8e-4a8e-bb57-651fb681004f	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
0e3adcb4-92b7-45a3-9ae4-757737d93224	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:10.507079+01	2026-11-13 16:02:11.445385+01	2026-11-13 16:02:10.497528+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	b6d28120-de0a-49d4-b0d7-f1eefafe0262	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
7888d47e-1930-488f-8953-35d56bd0a75e	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:11.583863+01	2026-11-13 16:02:12.514615+01	2026-11-13 16:02:11.579519+01	{}	{"add_one_resource": "true"}	t	f	t	3	98d1f457-cf79-4042-b779-5559fa3d2ae2	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
9c9de8be-9ab2-4991-917a-7496c10202ce	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:12.675674+01	2026-11-13 16:02:13.605303+01	2026-11-13 16:02:12.664255+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	9bd322c7-c881-4891-b99a-9b154c43268f	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
933f4eab-13e5-4fd4-a056-08590976f94e	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:13.710088+01	2026-11-13 16:02:14.66845+01	2026-11-13 16:02:13.65867+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	cd7ef40c-06b5-4c96-ba50-8832475ade7b	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f105c461-fdee-4b3d-bb51-aee6b1963a52	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:14.770731+01	2026-11-13 16:02:22.848828+01	2026-11-13 16:02:14.756015+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	aeaa8f3b-a155-4990-85c9-d39c1375551d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
b92caf56-a0aa-40bb-9bb2-43f3b767f401	4497d6a2-4aca-4d36-993a-0f6459475158	2026-11-13 16:02:23.712181+01	2026-11-13 16:02:23.715457+01	2026-11-13 16:02:23.700248+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	a205494d-8bc7-4142-9e55-da84f62d6433	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
2	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2026-11-13 16:02:23.419851+01	t	\N	9	\N	t	\N	\N
1	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:01.443064+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	616dfc7b-e970-4004-b040-b33fcdb1b963	2026-11-13 16:02:10.315016+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:11.424875+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2026-11-13 16:02:23.573893+01	f	\N	7	\N	t	\N	\N
3	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:12.501139+01	t	{"export_metadata": {"type": "manual", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:13.594353+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:14.655454+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:22.837389+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:22.899516+01	t	\N	3	6	t	\N	\N
8	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:02:23.068531+01	t	\N	2	7	t	\N	\N
1	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2026-11-13 16:02:23.265403+01	t	\N	6	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	1	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	1	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	1	fs	1.2.0	{}
616dfc7b-e970-4004-b040-b33fcdb1b963	1	mitogen	0.2.5	{}
616dfc7b-e970-4004-b040-b33fcdb1b963	1	std	7.0.0	{}
616dfc7b-e970-4004-b040-b33fcdb1b963	1	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	2	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	2	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	2	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	3	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	3	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	3	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	4	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	4	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	4	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	5	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	5	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	5	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	6	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	6	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	6	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	7	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	7	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	7	std	8.7.5	{}
8848d954-8550-43c8-8784-c56446578137	8	fs	1.2.0	{}
8848d954-8550-43c8-8784-c56446578137	8	mitogen	0.2.5	{}
8848d954-8550-43c8-8784-c56446578137	8	std	8.7.5	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	discovery::Discovered[myagent,name=discovered]	{}	2026-11-13 16:02:23.581357+01	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
8848d954-8550-43c8-8784-c56446578137	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-11-13 16:02:23.58138+01	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
b6c5a822-959d-4f04-922d-fad264b2e17e	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	2026-11-13 16:02:23.404089+01	6	0	{"11063fb1-5596-547b-9cc9-cf5de97a124e": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "1ab2dc7e-fe7f-5767-9370-8dc469129ef0": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "564fee7f-d458-5bb9-ab33-0341cfa1f7e8": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "6fbb6c2f-cc87-556d-822a-2c34cf45b70e": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}}, "cca0866e-c0ff-5221-aa8a-509df9cc3472": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "ff2a3870-607e-5da0-b695-af30b525d1b0": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
94295a98-8135-4d1b-95b3-5c77ec84fe27	dev-2	08d27da9-3ff9-4c70-9314-8b84ca80f0f4			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
616dfc7b-e970-4004-b040-b33fcdb1b963	dev-1-twin	08d27da9-3ff9-4c70-9314-8b84ca80f0f4			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
8848d954-8550-43c8-8784-c56446578137	dev-1	08d27da9-3ff9-4c70-9314-8b84ca80f0f4			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
4497d6a2-4aca-4d36-993a-0f6459475158	dev-4	08d27da9-3ff9-4c70-9314-8b84ca80f0f4			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	dev-3	08d27da9-3ff9-4c70-9314-8b84ca80f0f4			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
mitogen	0.2.5	8848d954-8550-43c8-8784-c56446578137	{}	f
std	8.7.5	8848d954-8550-43c8-8784-c56446578137	{}	f
fs	1.2.0	8848d954-8550-43c8-8784-c56446578137	{}	f
mitogen	0.2.5	616dfc7b-e970-4004-b040-b33fcdb1b963	{}	f
std	7.0.0	616dfc7b-e970-4004-b040-b33fcdb1b963	{}	f
fs	1.2.0	616dfc7b-e970-4004-b040-b33fcdb1b963	{}	f
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
47cbde98-7b5f-41b3-aad0-d8eaaa39b351	4497d6a2-4aca-4d36-993a-0f6459475158	2026-11-13 16:02:23.716731+01	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/b92caf56-a0aa-40bb-9bb2-43f3b767f401	f	f	b92caf56-a0aa-40bb-9bb2-43f3b767f401
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
d031b4dd-74d1-49ba-bc2a-b04ca144c533	fact1	value1	8848d954-8550-43c8-8784-c56446578137	std::testing::NullResource[localhost,name=test1]	fact	2026-11-13 16:02:13.642716+01	{}	f
beb55836-0815-4cd1-a8d4-054c1fd0d6d8	fact2	value2	8848d954-8550-43c8-8784-c56446578137	std::testing::NullResource[localhost,name=test2]	fact	2026-11-13 16:02:13.645833+01	{}	t
03a7ff82-e295-40cf-9911-bc3c89b4f884	fact3	value3	8848d954-8550-43c8-8784-c56446578137	std::testing::NullResource[localhost,name=test3]	fact	2026-11-13 16:02:13.6485+01	{}	t
141e3314-06f5-4683-8666-2422c9d54e50	parameter1	value1	8848d954-8550-43c8-8784-c56446578137		fact	2026-11-13 16:02:13.651063+01	{}	f
d7d69266-9ac3-49cf-a16a-2d10765df975	parameter2	value2	8848d954-8550-43c8-8784-c56446578137		fact	2026-11-13 16:02:13.653702+01	{}	f
1417cfd0-69de-4497-9966-9125395222fc	parameter3	value3	8848d954-8550-43c8-8784-c56446578137		fact	2026-11-13 16:02:13.656382+01	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
08d27da9-3ff9-4c70-9314-8b84ca80f0f4	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
d3f77e2c-c258-4ea6-ae93-1d2fafc45dd7	2026-11-13 16:01:52.132131+01	2026-11-13 16:01:52.135273+01		Init		Using extra environment variables during compile \n	0	f032f615-0006-4cfe-9010-7cc7f775d914
0f3568eb-45fa-4feb-a7c6-0ed4832938b1	2026-11-13 16:01:52.135625+01	2026-11-13 16:01:52.137292+01		Venv check		Creating new venv at /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env-py3.14\n	0	f032f615-0006-4cfe-9010-7cc7f775d914
bcbe0124-5349-4748-bca7-decabd3beb29	2026-11-13 16:02:10.507497+01	2026-11-13 16:02:10.510962+01		Init		Using extra environment variables during compile \n	0	0e3adcb4-92b7-45a3-9ae4-757737d93224
5aace779-203f-4d56-86ab-fff7c1c0ac2e	2026-11-13 16:01:52.138451+01	2026-11-13 16:01:52.340173+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	f032f615-0006-4cfe-9010-7cc7f775d914
595697bb-6964-4edb-ab41-9378d55cfd15	2026-11-13 16:01:52.341361+01	2026-11-13 16:02:00.518209+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmplmumreuz:\n                                 Pip command: /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmplmumreuz inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, python-dateutil, mitogen, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.2\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 mitogen-0.3.54 python-dateutil-3.0.0 texttable-1.7.3\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	f032f615-0006-4cfe-9010-7cc7f775d914
9d89c7ba-c448-42ac-9b45-23d56f0b2abe	2026-11-13 16:02:00.519513+01	2026-11-13 16:02:01.463886+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp261joq82 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.012 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.026 seconds\ncompiler       DEBUG   The entire export command took 0.074 seconds\n	0	f032f615-0006-4cfe-9010-7cc7f775d914
e237c504-aef8-4b89-84cb-1b9e9734ecf6	2026-11-13 16:02:10.511423+01	2026-11-13 16:02:10.512258+01		Venv check		Found existing venv\n	0	0e3adcb4-92b7-45a3-9ae4-757737d93224
6cdae759-c8a4-4699-a8d4-025abd499e53	2026-11-13 16:02:01.740485+01	2026-11-13 16:02:01.74297+01		Init		Using extra environment variables during compile \n	0	9609dc26-dc6b-4cc6-a26a-fb334feaf8d5
311e547a-f0bc-412b-b9cc-11975ca13ae4	2026-11-13 16:02:01.743238+01	2026-11-13 16:02:01.744738+01		Venv check		Creating new venv at /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env-py3.14\n	0	9609dc26-dc6b-4cc6-a26a-fb334feaf8d5
9c554489-bd26-4410-b6ae-b57a87e83459	2026-11-13 16:02:12.676706+01	2026-11-13 16:02:12.679132+01		Init		Using extra environment variables during compile \n	0	9c9de8be-9ab2-4991-917a-7496c10202ce
4c83e2e8-5281-443d-9359-ef4f1d5e6991	2026-11-13 16:02:01.745986+01	2026-11-13 16:02:01.946458+01	/tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	9609dc26-dc6b-4cc6-a26a-fb334feaf8d5
8fdfe43c-a351-4870-8280-f230fbc003a2	2026-11-13 16:02:10.512528+01	2026-11-13 16:02:11.444797+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpmext3i1i --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.066 seconds\n	0	0e3adcb4-92b7-45a3-9ae4-757737d93224
15f108a8-3b9b-4e67-aedd-6ac19d64dda3	2026-11-13 16:02:11.584216+01	2026-11-13 16:02:11.586485+01		Init		Using extra environment variables during compile add_one_resource='true'\n	0	7888d47e-1930-488f-8953-35d56bd0a75e
b4715175-2fad-41b3-b957-0a75d5826e0c	2026-11-13 16:02:13.721055+01	2026-11-13 16:02:13.723108+01		Venv check		Found existing venv\n	0	933f4eab-13e5-4fd4-a056-08590976f94e
438fd1ac-f4a2-4b66-a0ca-a85566511b74	2026-11-13 16:02:11.586762+01	2026-11-13 16:02:11.587211+01		Venv check		Found existing venv\n	0	7888d47e-1930-488f-8953-35d56bd0a75e
e3ff33f4-dd8d-4669-8fd7-717de7e2401a	2026-11-13 16:02:12.679379+01	2026-11-13 16:02:12.679815+01		Venv check		Found existing venv\n	0	9c9de8be-9ab2-4991-917a-7496c10202ce
1f54041d-25b2-4f3d-9bc0-4d1bf260147a	2026-11-13 16:02:11.587414+01	2026-11-13 16:02:12.514037+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpevba85ik --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.019 seconds\ncompiler       DEBUG   The entire export command took 0.063 seconds\n	0	7888d47e-1930-488f-8953-35d56bd0a75e
23076adb-3022-410c-82f5-1169ffef80f1	2026-11-13 16:02:12.679998+01	2026-11-13 16:02:13.604973+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmprg2cazmz --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.054 seconds\n	0	9c9de8be-9ab2-4991-917a-7496c10202ce
874083af-9ac4-4414-97f2-c4a60c63832d	2026-11-13 16:02:13.711933+01	2026-11-13 16:02:13.720052+01		Init		Using extra environment variables during compile \n	0	933f4eab-13e5-4fd4-a056-08590976f94e
825120f0-f783-4be5-8546-69526f8fc069	2026-11-13 16:02:13.724013+01	2026-11-13 16:02:14.668032+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp9ce30k1l --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.014 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	933f4eab-13e5-4fd4-a056-08590976f94e
99fef9ce-53e9-44c1-951c-a82c4f4971ef	2026-11-13 16:02:23.713308+01	2026-11-13 16:02:23.715117+01		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp8rvh721x/server/4497d6a2-4aca-4d36-993a-0f6459475158/compiler and no repository set.\n	1	b92caf56-a0aa-40bb-9bb2-43f3b767f401
23ce546c-ad0f-479b-9a4d-2bfbac7b386b	2026-11-13 16:02:01.947374+01	2026-11-13 16:02:09.40432+01	/tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpqak1js9b:\n                                 Pip command: /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpqak1js9b inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Collecting python-dateutil<4,>=2.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached python_dateutil-3.0.0-py2.py3-none-any.whl (94 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, python-dateutil, mitogen, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.2\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-dateutil\ninmanta.pip              DEBUG   Found existing installation: python-dateutil 2.9.0.post0\ninmanta.pip              DEBUG   Not uninstalling python-dateutil at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-dateutil'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 mitogen-0.3.54 python-dateutil-3.0.0 texttable-1.7.3\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	9609dc26-dc6b-4cc6-a26a-fb334feaf8d5
19e7c1cc-aa72-4036-92c2-e2e3ea05df67	2026-11-13 16:02:09.404947+01	2026-11-13 16:02:10.329131+01	/tmp/tmp8rvh721x/server/616dfc7b-e970-4004-b040-b33fcdb1b963/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 616dfc7b-e970-4004-b040-b33fcdb1b963 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpu3_xswg8 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.016 seconds\ncompiler       DEBUG   The entire export command took 0.059 seconds\n	0	9609dc26-dc6b-4cc6-a26a-fb334feaf8d5
663f472d-5eb4-4900-96ed-7ca0fe9db181	2026-11-13 16:02:14.771122+01	2026-11-13 16:02:14.773063+01		Init		Using extra environment variables during compile \n	0	f105c461-fdee-4b3d-bb51-aee6b1963a52
14efc604-4bce-4f91-926a-a44aa88cc156	2026-11-13 16:02:14.773339+01	2026-11-13 16:02:14.773849+01		Venv check		Found existing venv\n	0	f105c461-fdee-4b3d-bb51-aee6b1963a52
f2154660-2831-4942-b6d7-c0b31160d693	2026-11-13 16:02:14.775198+01	2026-11-13 16:02:14.97542+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages, outside environment /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	f105c461-fdee-4b3d-bb51-aee6b1963a52
2dc21c24-11ef-49c0-9a1c-3ebe87ba9863	2026-11-13 16:02:14.975871+01	2026-11-13 16:02:21.922796+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp0clddcc7:\n                                 Pip command: /tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp0clddcc7 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil<4,>=2.0 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.8)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.342,>=0.318.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.6 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-dateutil<4,>=2.0->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-graphql<0.342,>=0.318.1->inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	f105c461-fdee-4b3d-bb51-aee6b1963a52
1a8170ea-fb2d-4570-b899-3f67508e1701	2026-11-13 16:02:21.923263+01	2026-11-13 16:02:22.848522+01	/tmp/tmp8rvh721x/server/8848d954-8550-43c8-8784-c56446578137/compiler/.env/bin/python3 -m inmanta.app -vvv export -X -e 8848d954-8550-43c8-8784-c56446578137 --server_address localhost --server_port 39511 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpxp3k4cow --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:39511/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:39511/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.013 seconds\ncompiler       DEBUG   The entire export command took 0.056 seconds\n	0	f105c461-fdee-4b3d-bb51-aee6b1963a52
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	c376ad23-c16e-40b2-b797-08ef6e510473
616dfc7b-e970-4004-b040-b33fcdb1b963	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	a06f9517-1f22-46bb-a1fc-bcad10f7543c
616dfc7b-e970-4004-b040-b33fcdb1b963	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a06f9517-1f22-46bb-a1fc-bcad10f7543c
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	ec636691-42ed-43cb-b06b-832c80e10a84
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	acb1f55d-0232-4fb2-91db-7c29eb27f641
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	acb1f55d-0232-4fb2-91db-7c29eb27f641
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	3979f30f-fe21-4917-8356-1c87f94af2cd
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	479827ba-2d2e-421c-b0d2-c8eaaeebec0a
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	337f37a7-48ad-4bf8-966e-e6dcbe19beb6
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a6840358-e1da-4465-9a36-724f9ecaef14
8848d954-8550-43c8-8784-c56446578137	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	54abf7f8-5c53-40dc-ad28-b30af84f0ed2
8848d954-8550-43c8-8784-c56446578137	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	4a0e5303-aed0-4aef-aa27-bb12169b56ce
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6b19318f-078d-4116-99d2-412d6497393a
8848d954-8550-43c8-8784-c56446578137	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	761b5a48-d325-4faf-bfab-aee6870350e3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
e634a828-67aa-41a1-bf3d-03f976b6d7bd	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-11-13 16:02:23.43807+01
b4468171-e08d-4df0-aff7-d4fde9490cae	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-11-13 16:02:23.452431+01
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Fail[agent1,key=key2]	2026-11-13 16:02:23.278279+01	\N	2026-11-13 16:02:23.278279+01	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:23.269862+01	f	\N	\N
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test]	2026-11-13 16:02:01.60837+01	\N	2026-11-13 16:02:01.60837+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:01.59277+01	f	\N	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key10]	2026-11-13 16:02:23.452431+01	\N	2026-11-13 16:02:23.452431+01	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.426605+01	f	b4468171-e08d-4df0-aff7-d4fde9490cae	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key3]	2026-11-13 16:02:23.281333+01	\N	2026-11-13 16:02:23.281333+01	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-11-13 16:02:23.269862+01	f	\N	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	std::AgentConfig[internal,agentname=localhost]	2026-11-13 16:02:10.373305+01	\N	2026-11-13 16:02:10.373305+01	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:10.366054+01	f	\N	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	fs::File[localhost,path=/tmp/test]	2026-11-13 16:02:10.379884+01	\N	2026-11-13 16:02:10.379884+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:10.366054+01	f	\N	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key1]	2026-11-13 16:02:23.290818+01	2026-11-13 16:02:23.287071+01	2026-11-13 16:02:23.290818+01	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.269862+01	t	\N	\N
8848d954-8550-43c8-8784-c56446578137	fs::File[localhost,path=/tmp/test_orphan]	2026-11-13 16:02:12.539606+01	\N	2026-11-13 16:02:12.539606+01	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:12.533569+01	f	\N	3
8848d954-8550-43c8-8784-c56446578137	test::Resource[agent2,key=key2]	2026-11-13 16:02:22.944274+01	\N	2026-11-13 16:02:22.944274+01	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:22.933033+01	f	\N	\N
8848d954-8550-43c8-8784-c56446578137	test::Resource[agent3,key=key3]	2026-11-13 16:02:22.942486+01	\N	2026-11-13 16:02:22.942486+01	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-11-13 16:02:22.933033+01	f	\N	7
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-11-13 16:02:23.269862+01	\N	\N	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-11-13 16:02:23.269862+01	\N	\N	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key6]	2026-11-13 16:02:23.286195+01	2026-11-13 16:02:23.282076+01	2026-11-13 16:02:23.286195+01	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.269862+01	t	\N	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key11]	2026-11-13 16:02:23.43807+01	\N	2026-11-13 16:02:23.43807+01	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.426605+01	f	e634a828-67aa-41a1-bf3d-03f976b6d7bd	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key9]	2026-11-13 16:02:23.442977+01	2026-11-13 16:02:23.439435+01	2026-11-13 16:02:23.442977+01	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.426605+01	t	\N	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	test::Resource[agent1,key=key7]	2026-11-13 16:02:23.448066+01	2026-11-13 16:02:23.443916+01	2026-11-13 16:02:23.448066+01	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-13 16:02:23.426605+01	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	c376ad23-c16e-40b2-b797-08ef6e510473	\N
616dfc7b-e970-4004-b040-b33fcdb1b963	a06f9517-1f22-46bb-a1fc-bcad10f7543c	\N
8848d954-8550-43c8-8784-c56446578137	ec636691-42ed-43cb-b06b-832c80e10a84	\N
8848d954-8550-43c8-8784-c56446578137	acb1f55d-0232-4fb2-91db-7c29eb27f641	\N
8848d954-8550-43c8-8784-c56446578137	3979f30f-fe21-4917-8356-1c87f94af2cd	\N
8848d954-8550-43c8-8784-c56446578137	479827ba-2d2e-421c-b0d2-c8eaaeebec0a	\N
8848d954-8550-43c8-8784-c56446578137	337f37a7-48ad-4bf8-966e-e6dcbe19beb6	\N
8848d954-8550-43c8-8784-c56446578137	a6840358-e1da-4465-9a36-724f9ecaef14	\N
8848d954-8550-43c8-8784-c56446578137	54abf7f8-5c53-40dc-ad28-b30af84f0ed2	set-b
8848d954-8550-43c8-8784-c56446578137	4a0e5303-aed0-4aef-aa27-bb12169b56ce	set-a
8848d954-8550-43c8-8784-c56446578137	6b19318f-078d-4116-99d2-412d6497393a	\N
8848d954-8550-43c8-8784-c56446578137	761b5a48-d325-4faf-bfab-aee6870350e3	set-a
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	a4b0396c-8292-4ff4-aaf4-347495795a1f	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	24506162-3c35-439e-b9e2-58e55794533e	\N
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	1	c376ad23-c16e-40b2-b797-08ef6e510473
616dfc7b-e970-4004-b040-b33fcdb1b963	1	a06f9517-1f22-46bb-a1fc-bcad10f7543c
8848d954-8550-43c8-8784-c56446578137	2	ec636691-42ed-43cb-b06b-832c80e10a84
8848d954-8550-43c8-8784-c56446578137	3	acb1f55d-0232-4fb2-91db-7c29eb27f641
8848d954-8550-43c8-8784-c56446578137	4	3979f30f-fe21-4917-8356-1c87f94af2cd
8848d954-8550-43c8-8784-c56446578137	5	479827ba-2d2e-421c-b0d2-c8eaaeebec0a
8848d954-8550-43c8-8784-c56446578137	6	337f37a7-48ad-4bf8-966e-e6dcbe19beb6
8848d954-8550-43c8-8784-c56446578137	7	a6840358-e1da-4465-9a36-724f9ecaef14
8848d954-8550-43c8-8784-c56446578137	7	54abf7f8-5c53-40dc-ad28-b30af84f0ed2
8848d954-8550-43c8-8784-c56446578137	7	4a0e5303-aed0-4aef-aa27-bb12169b56ce
8848d954-8550-43c8-8784-c56446578137	8	6b19318f-078d-4116-99d2-412d6497393a
8848d954-8550-43c8-8784-c56446578137	8	761b5a48-d325-4faf-bfab-aee6870350e3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	a4b0396c-8292-4ff4-aaf4-347495795a1f
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	24506162-3c35-439e-b9e2-58e55794533e
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	3	d6dcdb59-d8ae-4114-bbdd-f74dbc556c9d
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
49f3d78b-0315-4ac0-8454-53ba13063103	store	2026-11-13 16:02:01.44301+01	2026-11-13 16:02:01.449923+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-13T16:02:01.449935+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	1	{"fs::File[localhost,path=/tmp/test],v=1"}
6d697d40-a9d7-44c1-8f56-7c72d4436eaf	deploy	2026-11-13 16:02:01.599916+01	2026-11-13 16:02:01.60837+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:01.607566+01:00\\"}"}	unavailable	\N	nochange	8848d954-8550-43c8-8784-c56446578137	1	{"fs::File[localhost,path=/tmp/test],v=1"}
66d5d8c9-6952-42bd-9d05-1cc6336756fa	store	2026-11-13 16:02:10.314962+01	2026-11-13 16:02:10.320692+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-13T16:02:10.320702+01:00\\"}"}	\N	\N	\N	616dfc7b-e970-4004-b040-b33fcdb1b963	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
49325650-374a-4246-a2fb-da9c5f3d0de4	deploy	2026-11-13 16:02:10.371621+01	2026-11-13 16:02:10.373305+01	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:10.372751+01:00\\"}"}	unavailable	\N	nochange	616dfc7b-e970-4004-b040-b33fcdb1b963	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
36c5172b-fca2-442f-899c-492726ad436b	deploy	2026-11-13 16:02:10.378757+01	2026-11-13 16:02:10.379884+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:10.379478+01:00\\"}"}	unavailable	\N	nochange	616dfc7b-e970-4004-b040-b33fcdb1b963	1	{"fs::File[localhost,path=/tmp/test],v=1"}
e71cb6f7-5d2c-47d2-8761-873b0392d8a9	store	2026-11-13 16:02:11.424822+01	2026-11-13 16:02:11.430732+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-13T16:02:11.430741+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	2	{"fs::File[localhost,path=/tmp/test],v=2"}
b47f62b4-21c1-48ba-a595-286d1b17983b	store	2026-11-13 16:02:12.501083+01	2026-11-13 16:02:12.503672+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-13T16:02:12.503680+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
ef57b4ca-3637-4ffc-9497-532d72f36088	deploy	2026-11-13 16:02:12.537018+01	2026-11-13 16:02:12.539606+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-11-13T16:02:12.539090+01:00\\"}"}	unavailable	\N	nochange	8848d954-8550-43c8-8784-c56446578137	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
29f6b8e3-b4ad-4011-a574-7b03af8e0371	store	2026-11-13 16:02:13.594291+01	2026-11-13 16:02:13.596296+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-11-13T16:02:13.596305+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	4	{"fs::File[localhost,path=/tmp/test],v=4"}
f4475c6f-5f15-4c0e-a143-94e810563a0a	store	2026-11-13 16:02:14.655393+01	2026-11-13 16:02:14.65744+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-11-13T16:02:14.657449+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	5	{"fs::File[localhost,path=/tmp/test],v=5"}
06f95d0e-66a7-4967-9050-d955ee562ae1	store	2026-11-13 16:02:22.837318+01	2026-11-13 16:02:22.839615+01	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-11-13T16:02:22.839623+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	6	{"fs::File[localhost,path=/tmp/test],v=6"}
0bb2c2fc-b9a2-4a73-9861-a7768ce44988	store	2026-11-13 16:02:22.899412+01	2026-11-13 16:02:22.906729+01	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-11-13T16:02:22.906737+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7"}
9a2a8933-9142-43e1-8b63-2acd2fdeb919	deploy	2026-11-13 16:02:22.939959+01	2026-11-13 16:02:22.942486+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-11-13T16:02:22.941866+01:00\\"}"}	unavailable	\N	nochange	8848d954-8550-43c8-8784-c56446578137	7	{"test::Resource[agent3,key=key3],v=7"}
d0b55690-4dc1-42e1-a080-fa829baba0f4	deploy	2026-11-13 16:02:22.942543+01	2026-11-13 16:02:22.944274+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-11-13T16:02:22.943697+01:00\\"}"}	unavailable	\N	nochange	8848d954-8550-43c8-8784-c56446578137	7	{"test::Resource[agent2,key=key2],v=7"}
314cb453-9603-4751-a395-c7c2ff44758a	store	2026-11-13 16:02:23.068326+01	2026-11-13 16:02:23.089367+01	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-11-13T16:02:23.089385+01:00\\"}"}	\N	\N	\N	8848d954-8550-43c8-8784-c56446578137	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
b8690c6b-bc00-4469-9956-bc0899e92670	store	2026-11-13 16:02:23.265343+01	2026-11-13 16:02:23.267496+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-13T16:02:23.267504+01:00\\"}"}	\N	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key3],v=1"}
d8302f24-e2f5-40ec-a1c0-657583a397ec	deploy	2026-11-13 16:02:23.275376+01	2026-11-13 16:02:23.278279+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 57737c7c-a37a-460f-80be-6c74bdf205b8).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"57737c7c-a37a-460f-80be-6c74bdf205b8\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.276492+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/tests/conftest.py\\\\\\", line 2600, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.277573+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 57737c7c-a37a-460f-80be-6c74bdf205b8) - duration: 0.0017 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0016736984252929688, \\"deploy_id\\": \\"57737c7c-a37a-460f-80be-6c74bdf205b8\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.278221+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Fail[agent1,key=key2],v=1"}
96222d75-e426-43f5-9241-3fbf3136a477	deploy	2026-11-13 16:02:23.280404+01	2026-11-13 16:02:23.281333+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d00a3006-886e-4454-ae62-24f17ea706eb).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"d00a3006-886e-4454-ae62-24f17ea706eb\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.281080+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.281199+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: d00a3006-886e-4454-ae62-24f17ea706eb) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0001876354217529297, \\"deploy_id\\": \\"d00a3006-886e-4454-ae62-24f17ea706eb\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.281305+01:00\\"}"}	skipped	\N	nochange	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key3],v=1"}
28b78ffb-d7b3-4b65-999f-b1c8abc1fd68	deploy	2026-11-13 16:02:23.282102+01	2026-11-13 16:02:23.286195+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 73ba17ed-fe12-49ec-8b30-964dae4e64a0).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"73ba17ed-fe12-49ec-8b30-964dae4e64a0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.282714+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 73ba17ed-fe12-49ec-8b30-964dae4e64a0) - duration: 0.0034 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0034041404724121094, \\"deploy_id\\": \\"73ba17ed-fe12-49ec-8b30-964dae4e64a0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.286164+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key6],v=1"}
20dba0d0-2e13-4c7a-8590-7dc6a47b9356	deploy	2026-11-13 16:02:23.287098+01	2026-11-13 16:02:23.290818+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 84c8e6e9-8c39-4513-bc96-3eee6a21fdc0).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"84c8e6e9-8c39-4513-bc96-3eee6a21fdc0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.287719+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 84c8e6e9-8c39-4513-bc96-3eee6a21fdc0) - duration: 0.0030 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0030274391174316406, \\"deploy_id\\": \\"84c8e6e9-8c39-4513-bc96-3eee6a21fdc0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.290790+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key1],v=1"}
b68f5eea-8adc-4cd3-84e6-67f92109a718	store	2026-11-13 16:02:23.419767+01	2026-11-13 16:02:23.422377+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-13T16:02:23.422384+01:00\\"}"}	\N	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	{"test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key11],v=2"}
614e2478-a459-4672-b3cf-f44111edaa24	dryrun	2026-11-13 16:02:23.424509+01	2026-11-13 16:02:23.425154+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.424557+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005440711975097656, \\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.425141+01:00\\"}"}	dry	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key3],v=1"}
0b5dfd2a-e233-4e54-b5ee-4951a90f942a	dryrun	2026-11-13 16:02:23.413784+01	2026-11-13 16:02:23.414798+01	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.413904+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e - duration 0.0008 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007805824279785156, \\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.414773+01:00\\"}"}	dry	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Fail[agent1,key=key2],v=1"}
e7675412-a430-4f15-a851-9240da2a3f92	dryrun	2026-11-13 16:02:23.420555+01	2026-11-13 16:02:23.420999+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.420602+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00033736228942871094, \\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.420983+01:00\\"}"}	dry	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key1],v=1"}
bdb243a2-9961-4754-8dbd-f8f5f1e9b2e1	dryrun	2026-11-13 16:02:23.427529+01	2026-11-13 16:02:23.428018+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.427576+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003840923309326172, \\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.428005+01:00\\"}"}	dry	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key5],v=1"}
9e3c8219-41c0-4e1a-98ac-156ad1498ae4	deploy	2026-11-13 16:02:23.433103+01	2026-11-13 16:02:23.43807+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 60210b78-0e04-476a-9bb7-ce4a3a97bf99).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"60210b78-0e04-476a-9bb7-ce4a3a97bf99\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.433964+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.434438+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 60210b78-0e04-476a-9bb7-ce4a3a97bf99) - duration: 0.0040 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.004029512405395508, \\"deploy_id\\": \\"60210b78-0e04-476a-9bb7-ce4a3a97bf99\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.438036+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	{"test::Resource[agent1,key=key11],v=2"}
8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	store	2026-11-13 16:02:23.573847+01	2026-11-13 16:02:23.575599+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-13T16:02:23.575607+01:00\\"}"}	\N	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	3	{"test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key3],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key4],v=3"}
a80ace6f-8ea3-4fd0-8fff-de7108f7b2e4	deploy	2026-11-13 16:02:23.439464+01	2026-11-13 16:02:23.442977+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3733e29e-3404-41ec-9100-ecd101cf6854).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"3733e29e-3404-41ec-9100-ecd101cf6854\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.440040+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 3733e29e-3404-41ec-9100-ecd101cf6854) - duration: 0.0029 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0028600692749023438, \\"deploy_id\\": \\"3733e29e-3404-41ec-9100-ecd101cf6854\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.442942+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	{"test::Resource[agent1,key=key9],v=2"}
abd26c95-42d2-4312-9e98-c8c11e6c0bb9	deploy	2026-11-13 16:02:23.443944+01	2026-11-13 16:02:23.448066+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 5dee0f83-e54c-45dc-bab1-ecd50fdfeba0).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"5dee0f83-e54c-45dc-bab1-ecd50fdfeba0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.444996+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 5dee0f83-e54c-45dc-bab1-ecd50fdfeba0) - duration: 0.0030 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.0029952526092529297, \\"deploy_id\\": \\"5dee0f83-e54c-45dc-bab1-ecd50fdfeba0\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.448036+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	{"test::Resource[agent1,key=key7],v=2"}
d31487d9-baed-4325-a261-ba9f52de25c3	deploy	2026-11-13 16:02:23.448928+01	2026-11-13 16:02:23.452431+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: b57b1c13-aa96-47fe-8c9a-ccfa20d3785d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"b57b1c13-aa96-47fe-8c9a-ccfa20d3785d\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.449529+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.449790+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: b57b1c13-aa96-47fe-8c9a-ccfa20d3785d) - duration: 0.0028 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.002825498580932617, \\"deploy_id\\": \\"b57b1c13-aa96-47fe-8c9a-ccfa20d3785d\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.452397+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2	{"test::Resource[agent1,key=key10],v=2"}
99c8b9a0-b017-41e2-b942-c72eebbe1815	dryrun	2026-11-13 16:02:23.453325+01	2026-11-13 16:02:23.453677+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.453365+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: b6c5a822-959d-4f04-922d-fad264b2e17e - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002593994140625, \\"dry_run_id\\": \\"b6c5a822-959d-4f04-922d-fad264b2e17e\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-13T16:02:23.453666+01:00\\"}"}	dry	\N	\N	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	1	{"test::Resource[agent1,key=key6],v=1"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
8848d954-8550-43c8-8784-c56446578137	49f3d78b-0315-4ac0-8454-53ba13063103	fs::File[localhost,path=/tmp/test]	1
8848d954-8550-43c8-8784-c56446578137	6d697d40-a9d7-44c1-8f56-7c72d4436eaf	fs::File[localhost,path=/tmp/test]	1
616dfc7b-e970-4004-b040-b33fcdb1b963	66d5d8c9-6952-42bd-9d05-1cc6336756fa	fs::File[localhost,path=/tmp/test]	1
616dfc7b-e970-4004-b040-b33fcdb1b963	66d5d8c9-6952-42bd-9d05-1cc6336756fa	std::AgentConfig[internal,agentname=localhost]	1
616dfc7b-e970-4004-b040-b33fcdb1b963	49325650-374a-4246-a2fb-da9c5f3d0de4	std::AgentConfig[internal,agentname=localhost]	1
616dfc7b-e970-4004-b040-b33fcdb1b963	36c5172b-fca2-442f-899c-492726ad436b	fs::File[localhost,path=/tmp/test]	1
8848d954-8550-43c8-8784-c56446578137	e71cb6f7-5d2c-47d2-8761-873b0392d8a9	fs::File[localhost,path=/tmp/test]	2
8848d954-8550-43c8-8784-c56446578137	b47f62b4-21c1-48ba-a595-286d1b17983b	fs::File[localhost,path=/tmp/test]	3
8848d954-8550-43c8-8784-c56446578137	b47f62b4-21c1-48ba-a595-286d1b17983b	fs::File[localhost,path=/tmp/test_orphan]	3
8848d954-8550-43c8-8784-c56446578137	ef57b4ca-3637-4ffc-9497-532d72f36088	fs::File[localhost,path=/tmp/test_orphan]	3
8848d954-8550-43c8-8784-c56446578137	29f6b8e3-b4ad-4011-a574-7b03af8e0371	fs::File[localhost,path=/tmp/test]	4
8848d954-8550-43c8-8784-c56446578137	f4475c6f-5f15-4c0e-a143-94e810563a0a	fs::File[localhost,path=/tmp/test]	5
8848d954-8550-43c8-8784-c56446578137	06f95d0e-66a7-4967-9050-d955ee562ae1	fs::File[localhost,path=/tmp/test]	6
8848d954-8550-43c8-8784-c56446578137	0bb2c2fc-b9a2-4a73-9861-a7768ce44988	fs::File[localhost,path=/tmp/test]	7
8848d954-8550-43c8-8784-c56446578137	0bb2c2fc-b9a2-4a73-9861-a7768ce44988	test::Resource[agent2,key=key2]	7
8848d954-8550-43c8-8784-c56446578137	0bb2c2fc-b9a2-4a73-9861-a7768ce44988	test::Resource[agent3,key=key3]	7
8848d954-8550-43c8-8784-c56446578137	9a2a8933-9142-43e1-8b63-2acd2fdeb919	test::Resource[agent3,key=key3]	7
8848d954-8550-43c8-8784-c56446578137	d0b55690-4dc1-42e1-a080-fa829baba0f4	test::Resource[agent2,key=key2]	7
8848d954-8550-43c8-8784-c56446578137	314cb453-9603-4751-a395-c7c2ff44758a	fs::File[localhost,path=/tmp/test]	8
8848d954-8550-43c8-8784-c56446578137	314cb453-9603-4751-a395-c7c2ff44758a	test::Resource[agent2,key=key2]	8
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Fail[agent1,key=key2]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Resource[agent1,key=key1]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Resource[agent1,key=key6]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Resource[agent1,key=key4]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Resource[agent1,key=key5]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b8690c6b-bc00-4469-9956-bc0899e92670	test::Resource[agent1,key=key3]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	d8302f24-e2f5-40ec-a1c0-657583a397ec	test::Fail[agent1,key=key2]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	96222d75-e426-43f5-9241-3fbf3136a477	test::Resource[agent1,key=key3]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	28b78ffb-d7b3-4b65-999f-b1c8abc1fd68	test::Resource[agent1,key=key6]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	20dba0d0-2e13-4c7a-8590-7dc6a47b9356	test::Resource[agent1,key=key1]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	0b5dfd2a-e233-4e54-b5ee-4951a90f942a	test::Fail[agent1,key=key2]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key4]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key5]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Fail[agent1,key=key2]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key10]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key7]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key9]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key3]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key1]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	b68f5eea-8adc-4cd3-84e6-67f92109a718	test::Resource[agent1,key=key11]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	e7675412-a430-4f15-a851-9240da2a3f92	test::Resource[agent1,key=key1]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	614e2478-a459-4672-b3cf-f44111edaa24	test::Resource[agent1,key=key3]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	bdb243a2-9961-4754-8dbd-f8f5f1e9b2e1	test::Resource[agent1,key=key5]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	9e3c8219-41c0-4e1a-98ac-156ad1498ae4	test::Resource[agent1,key=key11]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	a80ace6f-8ea3-4fd0-8fff-de7108f7b2e4	test::Resource[agent1,key=key9]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	abd26c95-42d2-4312-9e98-c8c11e6c0bb9	test::Resource[agent1,key=key7]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	d31487d9-baed-4325-a261-ba9f52de25c3	test::Resource[agent1,key=key10]	2
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	99c8b9a0-b017-41e2-b942-c72eebbe1815	test::Resource[agent1,key=key6]	1
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key7]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key8]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key5]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key1]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key3]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Fail[agent1,key=key2]	3
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	8ebf3e3c-ea7a-4c8b-addc-b83d4d2a404d	test::Resource[agent1,key=key4]	3
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
616dfc7b-e970-4004-b040-b33fcdb1b963	1
8848d954-8550-43c8-8784-c56446578137	8
6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	8848d954-8550-43c8-8784-c56446578137	2026-11-13 16:01:51.871721+01	\N	a48c9f28-ac6d-4c91-a940-4130fa138eb0
arnaud-inmanta-laptop	616dfc7b-e970-4004-b040-b33fcdb1b963	2026-11-13 16:01:51.99566+01	\N	96fce0b4-e3b3-4ad1-a1dd-ff94c94a928b
arnaud-inmanta-laptop	6cbc1a05-7aa6-4ea7-b72b-2ced4b2de5af	2026-11-13 16:02:23.13609+01	2026-11-13 16:02:23.566515+01	4f0dfb62-46db-4445-9ffa-3f8419824702
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
-- Name: resource_requires_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_requires_index ON public.resource USING gin (((attributes -> 'requires'::text)) jsonb_path_ops);


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

--\unrestrict OhuSWprJVmRKfQwRt09C7Sa2v7RLRIrS7jgjSvbdtIwwqBrGBdWe5tqarzWU1No

