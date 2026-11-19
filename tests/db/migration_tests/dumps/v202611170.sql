--
-- PostgreSQL database dump
--

--\restrict 1nVxfwimzFayrq4iDRacJy2A8QJsXFbZ3YmVsXSgrqoo7zT5pZ6Y7NccgkCNatj

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

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
c0603fc7-facf-4d01-bf2a-d04fa767ea35	$__scheduler	f	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	$__scheduler	f	\N
6ab799b6-44be-4b26-b828-4a6b31bfc5b6	$__scheduler	f	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	localhost	f	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	internal	f	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	localhost	f	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	agent3	f	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	agent2	f	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	agent1	t	t
900ac41c-83ce-464d-bf86-18d9c42d800e	$__scheduler	t	t
f41a3f68-0bad-45fd-8474-4dd9f26d3ee0	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
1	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
1	internal	std	ce83f2f0-68fb-4022-9bc9-2d6aa852879d
1	localhost	fs	ce83f2f0-68fb-4022-9bc9-2d6aa852879d
2	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
2	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
3	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
3	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
4	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
4	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
5	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
5	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
6	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
6	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
7	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
7	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
8	localhost	fs	c0603fc7-facf-4d01-bf2a-d04fa767ea35
8	localhost	std	c0603fc7-facf-4d01-bf2a-d04fa767ea35
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
b3476a27-6323-4f7c-b84b-d4e51cc5a662	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:23:58.088095+01	2026-11-17 12:24:05.068366+01	2026-11-17 12:23:58.077857+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	68d54a77-7c68-4c2f-af74-46807ca54002	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
cc7e377d-9ea9-4a67-b5c6-034893193932	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	2026-11-17 12:24:05.266651+01	2026-11-17 12:24:12.429059+01	2026-11-17 12:24:05.260219+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	4e6ba33a-3722-48a9-94a2-781ddb7bc423	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
79311bb2-c476-4563-8d59-5b38bed01bcd	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:12.633206+01	2026-11-17 12:24:13.599201+01	2026-11-17 12:24:12.628886+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	b57c0780-3a67-4edd-a238-48bd00e74b9c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c0fc2eee-b762-47c5-8638-88b290b3ee05	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:13.735645+01	2026-11-17 12:24:14.665915+01	2026-11-17 12:24:13.725065+01	{}	{"add_one_resource": "true"}	t	f	t	3	f1b278e1-9c3e-4111-b445-c100f0299bb7	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
644665f0-41fe-45a7-af11-53012eaa4910	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:14.845845+01	2026-11-17 12:24:15.813541+01	2026-11-17 12:24:14.837059+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	d6df8358-41ed-4c68-a8c8-28548e3e01d6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6608550b-bdcd-4092-9ef9-b75cbd54bda9	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:15.972511+01	2026-11-17 12:24:16.920905+01	2026-11-17 12:24:15.969179+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	783a58ac-71d6-408c-905f-0a73b61b2cbc	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
62d3118c-cd27-4e62-9ab0-e63d47b3011b	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:17.077212+01	2026-11-17 12:24:21.019996+01	2026-11-17 12:24:17.073966+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	7dd55e3f-c383-4297-8413-e56f28d5b34d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c08d64f0-a566-4edb-bdd4-1c7071696f89	f41a3f68-0bad-45fd-8474-4dd9f26d3ee0	2026-11-17 12:24:21.891635+01	2026-11-17 12:24:21.894696+01	2026-11-17 12:24:21.882621+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	189e8b10-26b8-4bbe-b7bb-e2334bf9f2f1	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:05.040906+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	2026-11-17 12:24:12.408631+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:13.568509+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:14.650996+01	t	{"export_metadata": {"type": "manual", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:15.796036+01	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:16.905032+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:21.004726+01	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "bart", "hostname": "vedett", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:21.096333+01	t	\N	3	6	t	\N	\N
8	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:24:21.271131+01	t	\N	2	7	t	\N	\N
1	900ac41c-83ce-464d-bf86-18d9c42d800e	2026-11-17 12:24:21.439929+01	t	\N	6	\N	t	\N	\N
2	900ac41c-83ce-464d-bf86-18d9c42d800e	2026-11-17 12:24:21.600596+01	t	\N	9	\N	t	\N	\N
3	900ac41c-83ce-464d-bf86-18d9c42d800e	2026-11-17 12:24:21.752048+01	f	\N	7	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	fs	1.2.0	{}
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	mitogen	0.2.5	{}
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	std	7.0.0	{}
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	2	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	2	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	2	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	4	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	4	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	4	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	5	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	5	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	5	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	6	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	6	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	6	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	std	8.7.6.dev20261020033327	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	fs	1.2.0	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	mitogen	0.2.5	{}
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	std	8.7.6.dev20261020033327	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	discovery::Discovered[myagent,name=discovered]	{}	2026-11-17 12:24:21.760398+01	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
c0603fc7-facf-4d01-bf2a-d04fa767ea35	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-11-17 12:24:21.760438+01	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, resource_filter, context) FROM stdin;
4232e784-39fb-406d-be3a-697b1d2cafc6	900ac41c-83ce-464d-bf86-18d9c42d800e	1	2026-11-17 12:24:21.585154+01	6	\N	\N
\.


--
-- Data for Name: dryrun_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun_resource (dryrun_id, resource_id, changes, diff_status) FROM stdin;
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Resource[agent1,key=key4]	{}	undefined
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Fail[agent1,key=key2]	{"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}	\N
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Resource[agent1,key=key1]	{}	\N
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Resource[agent1,key=key3]	{"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}	\N
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Resource[agent1,key=key5]	{"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}	\N
4232e784-39fb-406d-be3a-697b1d2cafc6	test::Resource[agent1,key=key6]	{}	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
6ab799b6-44be-4b26-b828-4a6b31bfc5b6	dev-2	6ab0a735-d590-4e20-9416-b65c5d7a6920			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	dev-1-twin	6ab0a735-d590-4e20-9416-b65c5d7a6920			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
900ac41c-83ce-464d-bf86-18d9c42d800e	dev-3	6ab0a735-d590-4e20-9416-b65c5d7a6920			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
f41a3f68-0bad-45fd-8474-4dd9f26d3ee0	dev-4	6ab0a735-d590-4e20-9416-b65c5d7a6920			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
c0603fc7-facf-4d01-bf2a-d04fa767ea35	dev-1	6ab0a735-d590-4e20-9416-b65c5d7a6920			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
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
mitogen	0.2.5	c0603fc7-facf-4d01-bf2a-d04fa767ea35	{}	f
std	8.7.6.dev20261020033327	c0603fc7-facf-4d01-bf2a-d04fa767ea35	{}	f
fs	1.2.0	c0603fc7-facf-4d01-bf2a-d04fa767ea35	{}	f
mitogen	0.2.5	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	{}	f
std	7.0.0	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	{}	f
fs	1.2.0	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	{}	f
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
38bb5c1d-df12-4eeb-825f-4317b10d0b63	f41a3f68-0bad-45fd-8474-4dd9f26d3ee0	2026-11-17 12:24:21.896034+01	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/c08d64f0-a566-4edb-bdd4-1c7071696f89	f	f	c08d64f0-a566-4edb-bdd4-1c7071696f89
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
a0daa968-b8ea-4af0-bcba-0076c79d6958	fact1	value1	c0603fc7-facf-4d01-bf2a-d04fa767ea35	std::testing::NullResource[localhost,name=test1]	fact	2026-11-17 12:24:15.940631+01	{}	f
ab66c9e3-13f3-4f0c-abe2-e6b16dd483d4	fact2	value2	c0603fc7-facf-4d01-bf2a-d04fa767ea35	std::testing::NullResource[localhost,name=test2]	fact	2026-11-17 12:24:15.946139+01	{}	t
7caad03c-609e-4092-9d19-ea5b91cf7915	fact3	value3	c0603fc7-facf-4d01-bf2a-d04fa767ea35	std::testing::NullResource[localhost,name=test3]	fact	2026-11-17 12:24:15.951812+01	{}	t
1d1d3ffb-9899-4600-aece-bde74ddac486	parameter1	value1	c0603fc7-facf-4d01-bf2a-d04fa767ea35		fact	2026-11-17 12:24:15.956873+01	{}	f
f27cea4d-d90c-4fa6-ab3e-6fdef384b9ff	parameter2	value2	c0603fc7-facf-4d01-bf2a-d04fa767ea35		fact	2026-11-17 12:24:15.961091+01	{}	f
2365f977-6b2a-4495-9ca4-f79595e8a73c	parameter3	value3	c0603fc7-facf-4d01-bf2a-d04fa767ea35		fact	2026-11-17 12:24:15.965521+01	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
6ab0a735-d590-4e20-9416-b65c5d7a6920	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
4f53de0d-e648-44ee-97a4-f139d0d3f3eb	2026-11-17 12:24:11.502395+01	2026-11-17 12:24:12.428403+01	/tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env/bin/python -m inmanta.app -vvv export -X -e ce83f2f0-68fb-4022-9bc9-2d6aa852879d --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpx8vfhv5b --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.026 seconds\ncompiler       DEBUG   The entire export command took 0.066 seconds\n	0	cc7e377d-9ea9-4a67-b5c6-034893193932
c62b9332-01c4-406f-b41c-fbce7ccbb985	2026-11-17 12:23:58.088938+01	2026-11-17 12:23:58.093596+01		Init		Using extra environment variables during compile \n	0	b3476a27-6323-4f7c-b84b-d4e51cc5a662
2f4fc96d-a19e-42c9-bdb6-45e839404ef2	2026-11-17 12:24:05.319328+01	2026-11-17 12:24:05.57782+01	/tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	cc7e377d-9ea9-4a67-b5c6-034893193932
aa8d8405-ac98-4cfa-aa83-8168705ec52b	2026-11-17 12:23:58.094385+01	2026-11-17 12:23:58.12965+01		Venv check		Creating new venv at /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env-py3.14\n	0	b3476a27-6323-4f7c-b84b-d4e51cc5a662
d6df87d0-2cd9-48f8-ad74-8885708576f3	2026-11-17 12:23:58.132397+01	2026-11-17 12:23:58.363836+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b3476a27-6323-4f7c-b84b-d4e51cc5a662
1ac4e3fe-4834-42c6-9a3c-1029ccbcc3a2	2026-11-17 12:24:12.634465+01	2026-11-17 12:24:12.638941+01		Init		Using extra environment variables during compile \n	0	79311bb2-c476-4563-8d59-5b38bed01bcd
bec2ad47-b360-4823-a830-4349ac98497a	2026-11-17 12:24:13.74147+01	2026-11-17 12:24:14.665269+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpvo7fqda9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.022 seconds\ncompiler       DEBUG   The entire export command took 0.063 seconds\n	0	c0fc2eee-b762-47c5-8638-88b290b3ee05
ed97bdd7-b8b7-49e1-b6b7-af86751634fa	2026-11-17 12:24:12.639613+01	2026-11-17 12:24:12.640888+01		Venv check		Found existing venv\n	0	79311bb2-c476-4563-8d59-5b38bed01bcd
499f60ab-5dbb-4c11-aa82-c26e803dd39d	2026-11-17 12:23:58.364315+01	2026-11-17 12:24:04.148027+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.6.dev20261020033327\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp0a6in7uv:\n                                 Pip command: /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp0a6in7uv inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (8.7.6.dev20261020033327)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Collecting click<8.6,>=8.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting email-validator<3,>=1 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl.metadata (26 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl.metadata (4.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl.metadata (141 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl.metadata (10.0 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.5)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Collecting graphql-core<3.4,>=3.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl.metadata (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.11.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl.metadata (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email-validator<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl.metadata (5.8 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (6.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Collecting typing-inspection>=0.4.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.336.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mypy-extensions>=0.3.0 (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl.metadata (1.1 kB)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pycparser (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.10.19)\ninmanta.pip              DEBUG   Collecting certifi>=2023.5.7 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl.metadata (2.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Collecting cross-web>=0.6.0 (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl.metadata (5.1 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl.metadata (1.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Collecting markdown-it-py>=2.2.0 (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl.metadata (7.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl (126 kB)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl (366 kB)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl (86 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl (494 kB)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (2.3 MB)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl (360 kB)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl (5.1 kB)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl (2.0 MB)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl (135 kB)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl (396 kB)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl (27 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl (14 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl (62 kB)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl (348 kB)\ninmanta.pip              DEBUG   Installing collected packages: texttable, tzdata, typing-inspection, tornado, SQLAlchemy, python-slugify, pydantic-core, pycparser, pip, mypy-extensions, mitogen, markdown-it-py, jsonpath-ng, graphql-core, dnspython, cross-web, click, certifi, strawberry-graphql, pydantic, email-validator, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.2\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.5\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspection\ninmanta.pip              DEBUG   Found existing installation: typing-inspection 0.4.4\ninmanta.pip              DEBUG   Not uninstalling typing-inspection at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspection'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.5\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 9.1.3\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.50.1\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pycparser\ninmanta.pip              DEBUG   Found existing installation: pycparser 3.11\ninmanta.pip              DEBUG   Not uninstalling pycparser at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pycparser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.2.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: mypy-extensions\ninmanta.pip              DEBUG   Found existing installation: mypy_extensions 1.1.0\ninmanta.pip              DEBUG   Not uninstalling mypy-extensions at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'mypy_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: markdown-it-py\ninmanta.pip              DEBUG   Found existing installation: markdown-it-py 4.2.0\ninmanta.pip              DEBUG   Not uninstalling markdown-it-py at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'markdown-it-py'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.11.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: graphql-core\ninmanta.pip              DEBUG   Found existing installation: graphql-core 3.3.0\ninmanta.pip              DEBUG   Not uninstalling graphql-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'graphql-core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.9.0\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cross-web\ninmanta.pip              DEBUG   Found existing installation: cross-web 0.7.0\ninmanta.pip              DEBUG   Not uninstalling cross-web at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cross-web'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.5.0\ninmanta.pip              DEBUG   Not uninstalling click at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2026.10.19\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.336.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.14.1\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 2.3.0\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.9 certifi-2026.10.23 click-8.5.1 cross-web-0.9.0 dnspython-2.9.2 email-validator-2.4.0 graphql-core-3.3.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.16.0 markdown-it-py-4.3.0 mitogen-0.3.54 mypy-extensions-1.2.0 pip-26.3 pycparser-3.12 pydantic-2.14.3 pydantic-core-2.50.4 python-slugify-9.2.0 strawberry-graphql-0.341.2 texttable-1.7.3 tornado-6.6.1 typing-inspection-0.4.5 tzdata-2026.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	b3476a27-6323-4f7c-b84b-d4e51cc5a662
6067f5a7-22db-4f7a-af48-7984c411cd79	2026-11-17 12:24:05.578785+01	2026-11-17 12:24:11.50156+01	/tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.6.dev20261020033327\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpeqe37a1l:\n                                 Pip command: /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpeqe37a1l inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Collecting click<8.6,>=8.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Collecting email-validator<3,>=1 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl.metadata (26 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Collecting pip>=21.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl.metadata (4.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Collecting pydantic!=2.9.2,~=2.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl.metadata (141 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl.metadata (10.0 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.5)\ninmanta.pip              DEBUG   Collecting SQLAlchemy~=2.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Collecting graphql-core<3.4,>=3.3 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl.metadata (11 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.11.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0 (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl.metadata (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Collecting dnspython>=2.0.0 (from email-validator<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl.metadata (5.8 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Collecting pydantic-core==2.50.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (6.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Collecting typing-inspection>=0.4.4 (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.336.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl.metadata (6.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mypy-extensions>=0.3.0 (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl.metadata (1.1 kB)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Collecting pycparser (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl.metadata (9.7 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.10.19)\ninmanta.pip              DEBUG   Collecting certifi>=2023.5.7 (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl.metadata (2.5 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Collecting cross-web>=0.6.0 (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl.metadata (5.1 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Collecting tzdata (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl.metadata (1.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Collecting markdown-it-py>=2.2.0 (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl.metadata (7.9 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached click-8.5.1-py3-none-any.whl (126 kB)\ninmanta.pip              DEBUG   Using cached email_validator-2.4.0-py3-none-any.whl (36 kB)\ninmanta.pip              DEBUG   Using cached graphql_core-3.3.2-py3-none-any.whl (366 kB)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.16.0-py3-none-any.whl (86 kB)\ninmanta.pip              DEBUG   Using cached pydantic-2.14.3-py3-none-any.whl (494 kB)\ninmanta.pip              DEBUG   Using cached pydantic_core-2.50.4-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (2.3 MB)\ninmanta.pip              DEBUG   Using cached sqlalchemy-2.1.9-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (4.6 MB)\ninmanta.pip              DEBUG   Using cached texttable-1.7.3-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached dnspython-2.9.2-py3-none-any.whl (360 kB)\ninmanta.pip              DEBUG   Using cached mypy_extensions-1.2.0-py3-none-any.whl (5.1 kB)\ninmanta.pip              DEBUG   Using cached pip-26.3-py3-none-any.whl (2.0 MB)\ninmanta.pip              DEBUG   Using cached python_slugify-9.2.0-py3-none-any.whl (17 kB)\ninmanta.pip              DEBUG   Using cached certifi-2026.10.23-py3-none-any.whl (135 kB)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.341.2-py3-none-any.whl (396 kB)\ninmanta.pip              DEBUG   Using cached cross_web-0.9.0-py3-none-any.whl (27 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6.1-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (534 kB)\ninmanta.pip              DEBUG   Using cached typing_inspection-0.4.5-py3-none-any.whl (14 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Using cached pycparser-3.12-py3-none-any.whl (62 kB)\ninmanta.pip              DEBUG   Using cached markdown_it_py-4.3.0-py3-none-any.whl (96 kB)\ninmanta.pip              DEBUG   Using cached tzdata-2026.6-py2.py3-none-any.whl (348 kB)\ninmanta.pip              DEBUG   Installing collected packages: texttable, tzdata, typing-inspection, tornado, SQLAlchemy, python-slugify, pydantic-core, pycparser, pip, mypy-extensions, mitogen, markdown-it-py, jsonpath-ng, graphql-core, dnspython, cross-web, click, certifi, strawberry-graphql, pydantic, email-validator, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.2\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tzdata\ninmanta.pip              DEBUG   Found existing installation: tzdata 2026.5\ninmanta.pip              DEBUG   Not uninstalling tzdata at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tzdata'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: typing-inspection\ninmanta.pip              DEBUG   Found existing installation: typing-inspection 0.4.4\ninmanta.pip              DEBUG   Not uninstalling typing-inspection at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'typing-inspection'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: SQLAlchemy\ninmanta.pip              DEBUG   Found existing installation: SQLAlchemy 2.1.5\ninmanta.pip              DEBUG   Not uninstalling sqlalchemy at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'SQLAlchemy'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 9.1.3\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic-core\ninmanta.pip              DEBUG   Found existing installation: pydantic_core 2.50.1\ninmanta.pip              DEBUG   Not uninstalling pydantic-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic_core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pycparser\ninmanta.pip              DEBUG   Found existing installation: pycparser 3.11\ninmanta.pip              DEBUG   Not uninstalling pycparser at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pycparser'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pip\ninmanta.pip              DEBUG   Found existing installation: pip 26.2.1\ninmanta.pip              DEBUG   Not uninstalling pip at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pip'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: mypy-extensions\ninmanta.pip              DEBUG   Found existing installation: mypy_extensions 1.1.0\ninmanta.pip              DEBUG   Not uninstalling mypy-extensions at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'mypy_extensions'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: markdown-it-py\ninmanta.pip              DEBUG   Found existing installation: markdown-it-py 4.2.0\ninmanta.pip              DEBUG   Not uninstalling markdown-it-py at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'markdown-it-py'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.11.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: graphql-core\ninmanta.pip              DEBUG   Found existing installation: graphql-core 3.3.0\ninmanta.pip              DEBUG   Not uninstalling graphql-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'graphql-core'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: dnspython\ninmanta.pip              DEBUG   Found existing installation: dnspython 2.9.0\ninmanta.pip              DEBUG   Not uninstalling dnspython at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'dnspython'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cross-web\ninmanta.pip              DEBUG   Found existing installation: cross-web 0.7.0\ninmanta.pip              DEBUG   Not uninstalling cross-web at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cross-web'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: click\ninmanta.pip              DEBUG   Found existing installation: click 8.5.0\ninmanta.pip              DEBUG   Not uninstalling click at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'click'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: certifi\ninmanta.pip              DEBUG   Found existing installation: certifi 2026.10.19\ninmanta.pip              DEBUG   Not uninstalling certifi at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'certifi'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.336.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: pydantic\ninmanta.pip              DEBUG   Found existing installation: pydantic 2.14.1\ninmanta.pip              DEBUG   Not uninstalling pydantic at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'pydantic'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: email-validator\ninmanta.pip              DEBUG   Found existing installation: email-validator 2.3.0\ninmanta.pip              DEBUG   Not uninstalling email-validator at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'email-validator'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.6.dev20261020033327\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed SQLAlchemy-2.1.9 certifi-2026.10.23 click-8.5.1 cross-web-0.9.0 dnspython-2.9.2 email-validator-2.4.0 graphql-core-3.3.2 inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.16.0 markdown-it-py-4.3.0 mitogen-0.3.54 mypy-extensions-1.2.0 pip-26.3 pycparser-3.12 pydantic-2.14.3 pydantic-core-2.50.4 python-slugify-9.2.0 strawberry-graphql-0.341.2 texttable-1.7.3 tornado-6.6.1 typing-inspection-0.4.5 tzdata-2026.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.6.dev20261020033327\n	0	cc7e377d-9ea9-4a67-b5c6-034893193932
c66b1677-f03e-4f54-a157-648369f0cdcd	2026-11-17 12:24:04.148531+01	2026-11-17 12:24:05.067645+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpwbhwcxm4 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.034 seconds\ncompiler       DEBUG   The entire export command took 0.075 seconds\n	0	b3476a27-6323-4f7c-b84b-d4e51cc5a662
a42a6204-67c6-4a8b-a0b5-11d4f154a3d7	2026-11-17 12:24:05.267394+01	2026-11-17 12:24:05.270924+01		Init		Using extra environment variables during compile \n	0	cc7e377d-9ea9-4a67-b5c6-034893193932
e487df4c-21a2-4d7a-a13f-b09bd3232c9a	2026-11-17 12:24:05.271814+01	2026-11-17 12:24:05.316352+01		Venv check		Creating new venv at /tmp/tmprdp1e3_y/server/ce83f2f0-68fb-4022-9bc9-2d6aa852879d/compiler/.env-py3.14\n	0	cc7e377d-9ea9-4a67-b5c6-034893193932
d0c04f8e-ce8e-44ac-b477-169387e755a1	2026-11-17 12:24:14.853747+01	2026-11-17 12:24:15.812914+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpn40r51ts --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.021 seconds\ncompiler       DEBUG   The entire export command took 0.065 seconds\n	0	644665f0-41fe-45a7-af11-53012eaa4910
142a5a24-5a1e-4b7e-8a5d-be6388af6382	2026-11-17 12:24:12.64146+01	2026-11-17 12:24:13.598621+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcfar01nt --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.035 seconds\ncompiler       DEBUG   The entire export command took 0.079 seconds\n	0	79311bb2-c476-4563-8d59-5b38bed01bcd
33c51d16-ecc5-4e20-a17f-75acbc264e83	2026-11-17 12:24:14.847688+01	2026-11-17 12:24:14.851895+01		Init		Using extra environment variables during compile \n	0	644665f0-41fe-45a7-af11-53012eaa4910
7817b6e3-6f19-42c3-b256-8f091c0790ce	2026-11-17 12:24:13.736233+01	2026-11-17 12:24:13.73943+01		Init		Using extra environment variables during compile add_one_resource='true'\n	0	c0fc2eee-b762-47c5-8638-88b290b3ee05
85f6ebd3-ce3d-4e67-ada3-d3d831343095	2026-11-17 12:24:13.739905+01	2026-11-17 12:24:13.740986+01		Venv check		Found existing venv\n	0	c0fc2eee-b762-47c5-8638-88b290b3ee05
09701eb6-8671-4a04-880c-03d0f48b675f	2026-11-17 12:24:14.852404+01	2026-11-17 12:24:14.853236+01		Venv check		Found existing venv\n	0	644665f0-41fe-45a7-af11-53012eaa4910
571555f2-a4c7-4474-9f8e-17c87c6594ce	2026-11-17 12:24:15.974325+01	2026-11-17 12:24:15.977797+01		Init		Using extra environment variables during compile \n	0	6608550b-bdcd-4092-9ef9-b75cbd54bda9
8853355a-51bc-4c2f-8ed7-23c08bd76d0a	2026-11-17 12:24:15.979826+01	2026-11-17 12:24:16.920218+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3al45ggd --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.020 seconds\ncompiler       DEBUG   The entire export command took 0.062 seconds\n	0	6608550b-bdcd-4092-9ef9-b75cbd54bda9
6e5dcc30-8d13-41f1-8938-928a33bda469	2026-11-17 12:24:15.97837+01	2026-11-17 12:24:15.979318+01		Venv check		Found existing venv\n	0	6608550b-bdcd-4092-9ef9-b75cbd54bda9
c2d275f4-1ac6-4ec6-a3fb-6cdc0cff8ae9	2026-11-17 12:24:17.078072+01	2026-11-17 12:24:17.080554+01		Init		Using extra environment variables during compile \n	0	62d3118c-cd27-4e62-9ab0-e63d47b3011b
ca3f6f61-0406-4acf-85cc-5c556fb0f260	2026-11-17 12:24:17.081068+01	2026-11-17 12:24:17.081988+01		Venv check		Found existing venv\n	0	62d3118c-cd27-4e62-9ab0-e63d47b3011b
d4bf66ac-9f79-4404-81e2-2ddd0c6fb7a8	2026-11-17 12:24:21.892347+01	2026-11-17 12:24:21.894452+01		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmprdp1e3_y/server/f41a3f68-0bad-45fd-8474-4dd9f26d3ee0/compiler and no repository set.\n	1	c08d64f0-a566-4edb-bdd4-1c7071696f89
8f83001b-2fe6-40db-9669-967c15f9cc23	2026-11-17 12:24:17.083792+01	2026-11-17 12:24:17.317828+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages, outside environment /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	62d3118c-cd27-4e62-9ab0-e63d47b3011b
55e8bff2-f5c0-4800-a031-8112f495ee92	2026-11-17 12:24:17.318127+01	2026-11-17 12:24:20.128335+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.6.dev20261020033327\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpwv6yels4:\n                                 Pip command: /tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpwv6yels4 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (8.7.6.dev20261020033327)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.3)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.3)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.9)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.2)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in ./.env/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.4 in ./.env/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in ./.env/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.5)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.341.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in ./.env/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in ./.env/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in ./.env/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in ./.env/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in ./.env/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in ./.env/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/bart/workspace/inmanta-core/.venv/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	62d3118c-cd27-4e62-9ab0-e63d47b3011b
35a86f9c-1dcb-4243-add7-6a5b975648f9	2026-11-17 12:24:20.128555+01	2026-11-17 12:24:21.019466+01	/tmp/tmprdp1e3_y/server/c0603fc7-facf-4d01-bf2a-d04fa767ea35/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c0603fc7-facf-4d01-bf2a-d04fa767ea35 --server_address localhost --server_port 47553 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpdup_r5xq --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.6.dev20261020033327\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/reserve_version\nexporter       INFO    Ignored 1 resources of type std::AgentConfig because they requested to be ignored\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.011 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47553/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47553/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.018 seconds\ncompiler       DEBUG   The entire export command took 0.059 seconds\n	0	62d3118c-cd27-4e62-9ab0-e63d47b3011b
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	52b2de15-c853-49d5-9c0c-6fe1b49d0ed1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	6c3ab73b-54ac-4cca-badf-e8738fd00853
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6c3ab73b-54ac-4cca-badf-e8738fd00853
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	38c9ea4d-7c32-4095-8f35-cfcc5ecc5a2d
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	cbc99bf9-762b-4bbf-a2ad-e93f4978c48f
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	cbc99bf9-762b-4bbf-a2ad-e93f4978c48f
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	65e47215-75c9-4d00-8b51-663ee26f53ac
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7a02ed98-b126-4661-a2f2-f1eafaf57adf
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	bfbffe25-fa37-487f-a7bb-4a00a978757a
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	8810f3e0-7dbe-4e47-aa9c-a8be754be905
c0603fc7-facf-4d01-bf2a-d04fa767ea35	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	bdf8674d-bf12-48dc-8b56-9bddf4d10725
c0603fc7-facf-4d01-bf2a-d04fa767ea35	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	d11c585c-370f-4fc8-b012-4c680ba1441e
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	01f93d20-bfa5-4229-b958-7a945fbf133c
c0603fc7-facf-4d01-bf2a-d04fa767ea35	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	d4a19183-38ce-4a6a-960a-f5c86e13cdc7
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	2213ca42-e6b7-41db-a5d7-f02abe2649d3
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
65032434-4f10-4924-a511-9487a327e721	900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-11-17 12:24:21.651065+01
0b3708e1-8517-413b-9b5e-49797e555031	900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-11-17 12:24:21.660898+01
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-11-17 12:24:21.443996+01	\N	\N	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test]	2026-11-17 12:24:05.149921+01	\N	2026-11-17 12:24:05.149921+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:05.128103+01	f	\N	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key1]	2026-11-17 12:24:21.459337+01	2026-11-17 12:24:21.450043+01	2026-11-17 12:24:21.459337+01	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.443996+01	t	\N	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key11]	2026-11-17 12:24:21.651065+01	\N	2026-11-17 12:24:21.651065+01	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.611946+01	f	65032434-4f10-4924-a511-9487a327e721	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Fail[agent1,key=key2]	2026-11-17 12:24:21.463116+01	\N	2026-11-17 12:24:21.463116+01	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:21.443996+01	f	\N	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	std::AgentConfig[internal,agentname=localhost]	2026-11-17 12:24:12.51685+01	\N	2026-11-17 12:24:12.51685+01	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:12.50519+01	f	\N	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	fs::File[localhost,path=/tmp/test]	2026-11-17 12:24:12.527819+01	\N	2026-11-17 12:24:12.527819+01	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:12.50519+01	f	\N	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key10]	2026-11-17 12:24:21.660898+01	\N	2026-11-17 12:24:21.660898+01	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.611946+01	f	0b3708e1-8517-413b-9b5e-49797e555031	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key3]	2026-11-17 12:24:21.470158+01	\N	2026-11-17 12:24:21.470158+01	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-11-17 12:24:21.443996+01	f	\N	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	fs::File[localhost,path=/tmp/test_orphan]	2026-11-17 12:24:14.717965+01	\N	2026-11-17 12:24:14.717965+01	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:14.709368+01	f	\N	3
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key7]	2026-11-17 12:24:21.667843+01	2026-11-17 12:24:21.662483+01	2026-11-17 12:24:21.667843+01	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.611946+01	t	\N	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	test::Resource[agent2,key=key2]	2026-11-17 12:24:21.144715+01	\N	2026-11-17 12:24:21.144715+01	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:21.130525+01	f	\N	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	test::Resource[agent3,key=key3]	2026-11-17 12:24:21.141101+01	\N	2026-11-17 12:24:21.141101+01	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-11-17 12:24:21.130525+01	f	\N	7
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-11-17 12:24:21.443996+01	\N	\N	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key6]	2026-11-17 12:24:21.46772+01	2026-11-17 12:24:21.463902+01	2026-11-17 12:24:21.46772+01	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.443996+01	t	\N	1
900ac41c-83ce-464d-bf86-18d9c42d800e	test::Resource[agent1,key=key9]	2026-11-17 12:24:21.643836+01	2026-11-17 12:24:21.618602+01	2026-11-17 12:24:21.643836+01	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-11-17 12:24:21.611946+01	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	52b2de15-c853-49d5-9c0c-6fe1b49d0ed1	\N
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	6c3ab73b-54ac-4cca-badf-e8738fd00853	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	38c9ea4d-7c32-4095-8f35-cfcc5ecc5a2d	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	cbc99bf9-762b-4bbf-a2ad-e93f4978c48f	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	65e47215-75c9-4d00-8b51-663ee26f53ac	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7a02ed98-b126-4661-a2f2-f1eafaf57adf	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	bfbffe25-fa37-487f-a7bb-4a00a978757a	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8810f3e0-7dbe-4e47-aa9c-a8be754be905	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	bdf8674d-bf12-48dc-8b56-9bddf4d10725	set-a
c0603fc7-facf-4d01-bf2a-d04fa767ea35	d11c585c-370f-4fc8-b012-4c680ba1441e	set-b
c0603fc7-facf-4d01-bf2a-d04fa767ea35	01f93d20-bfa5-4229-b958-7a945fbf133c	\N
c0603fc7-facf-4d01-bf2a-d04fa767ea35	d4a19183-38ce-4a6a-960a-f5c86e13cdc7	set-a
900ac41c-83ce-464d-bf86-18d9c42d800e	78c67130-ccf6-457b-a8a0-42f3d354b64f	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	546eff97-a7b3-422d-ae11-d647e4d4b3d5	\N
900ac41c-83ce-464d-bf86-18d9c42d800e	2213ca42-e6b7-41db-a5d7-f02abe2649d3	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	52b2de15-c853-49d5-9c0c-6fe1b49d0ed1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	6c3ab73b-54ac-4cca-badf-e8738fd00853
c0603fc7-facf-4d01-bf2a-d04fa767ea35	2	38c9ea4d-7c32-4095-8f35-cfcc5ecc5a2d
c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	cbc99bf9-762b-4bbf-a2ad-e93f4978c48f
c0603fc7-facf-4d01-bf2a-d04fa767ea35	4	65e47215-75c9-4d00-8b51-663ee26f53ac
c0603fc7-facf-4d01-bf2a-d04fa767ea35	5	7a02ed98-b126-4661-a2f2-f1eafaf57adf
c0603fc7-facf-4d01-bf2a-d04fa767ea35	6	bfbffe25-fa37-487f-a7bb-4a00a978757a
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	8810f3e0-7dbe-4e47-aa9c-a8be754be905
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	bdf8674d-bf12-48dc-8b56-9bddf4d10725
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	d11c585c-370f-4fc8-b012-4c680ba1441e
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	01f93d20-bfa5-4229-b958-7a945fbf133c
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	d4a19183-38ce-4a6a-960a-f5c86e13cdc7
900ac41c-83ce-464d-bf86-18d9c42d800e	1	78c67130-ccf6-457b-a8a0-42f3d354b64f
900ac41c-83ce-464d-bf86-18d9c42d800e	2	546eff97-a7b3-422d-ae11-d647e4d4b3d5
900ac41c-83ce-464d-bf86-18d9c42d800e	3	2213ca42-e6b7-41db-a5d7-f02abe2649d3
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
e5509da7-ac73-460d-b789-9757a92a3ff2	store	2026-11-17 12:24:05.040816+01	2026-11-17 12:24:05.049493+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-17T12:24:05.049509+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	{"fs::File[localhost,path=/tmp/test],v=1"}
deb4a6f9-bb45-4271-ad6b-933be6602d3c	deploy	2026-11-17 12:24:05.13878+01	2026-11-17 12:24:05.149921+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:05.149112+01:00\\"}"}	unavailable	\N	nochange	c0603fc7-facf-4d01-bf2a-d04fa767ea35	1	{"fs::File[localhost,path=/tmp/test],v=1"}
cf489afa-a1db-450a-a061-99a28580ed39	store	2026-11-17 12:24:12.408571+01	2026-11-17 12:24:12.416869+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-17T12:24:12.416882+01:00\\"}"}	\N	\N	\N	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
4a273f81-8cec-4b62-8103-ca30e46b469b	deploy	2026-11-17 12:24:12.515169+01	2026-11-17 12:24:12.51685+01	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:12.516314+01:00\\"}"}	unavailable	\N	nochange	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
ff96af8a-aea5-481d-8c9f-4a0f4251c6d7	deploy	2026-11-17 12:24:12.52581+01	2026-11-17 12:24:12.527819+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:12.527223+01:00\\"}"}	unavailable	\N	nochange	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1	{"fs::File[localhost,path=/tmp/test],v=1"}
8207c12e-fb37-40d2-bfb4-102a67fa9c24	store	2026-11-17 12:24:13.568426+01	2026-11-17 12:24:13.579634+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-17T12:24:13.579647+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2	{"fs::File[localhost,path=/tmp/test],v=2"}
7df52a6f-9b38-4613-8706-8f37b908a0f3	store	2026-11-17 12:24:14.650914+01	2026-11-17 12:24:14.654928+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-17T12:24:14.654941+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
6dc5c7c9-0201-4f2d-b8ec-78f35b68acdd	deploy	2026-11-17 12:24:14.71456+01	2026-11-17 12:24:14.717965+01	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-11-17T12:24:14.717297+01:00\\"}"}	unavailable	\N	nochange	c0603fc7-facf-4d01-bf2a-d04fa767ea35	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
59b3da42-280e-4026-adef-3d0ab0b301ec	store	2026-11-17 12:24:15.795954+01	2026-11-17 12:24:15.799858+01	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-11-17T12:24:15.799873+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	4	{"fs::File[localhost,path=/tmp/test],v=4"}
c2081776-b075-4ca5-b712-074edb921b89	store	2026-11-17 12:24:16.904941+01	2026-11-17 12:24:16.909326+01	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-11-17T12:24:16.909338+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	5	{"fs::File[localhost,path=/tmp/test],v=5"}
17d75d5b-4ee9-4e88-adfd-142b3f38f505	store	2026-11-17 12:24:21.004615+01	2026-11-17 12:24:21.00799+01	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-11-17T12:24:21.008007+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	6	{"fs::File[localhost,path=/tmp/test],v=6"}
931d38b2-ef00-420d-9094-9345393e4347	store	2026-11-17 12:24:21.096119+01	2026-11-17 12:24:21.102928+01	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-11-17T12:24:21.102941+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	{"test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7"}
4225041a-e482-4d1e-a6ea-3db292e2b3b5	deploy	2026-11-17 12:24:21.138538+01	2026-11-17 12:24:21.141101+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.140299+01:00\\"}"}	unavailable	\N	nochange	c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	{"test::Resource[agent3,key=key3],v=7"}
2c7f3e98-b753-43a5-b4ca-74139198a1a8	deploy	2026-11-17 12:24:21.141188+01	2026-11-17 12:24:21.144715+01	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.144040+01:00\\"}"}	unavailable	\N	nochange	c0603fc7-facf-4d01-bf2a-d04fa767ea35	7	{"test::Resource[agent2,key=key2],v=7"}
49e4c53c-19f8-4d60-a24d-d5fb86d2abb5	store	2026-11-17 12:24:21.270898+01	2026-11-17 12:24:21.277162+01	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-11-17T12:24:21.277179+01:00\\"}"}	\N	\N	\N	c0603fc7-facf-4d01-bf2a-d04fa767ea35	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
65d74dff-90c0-4ab4-a7fe-18ac128828ea	store	2026-11-17 12:24:21.439888+01	2026-11-17 12:24:21.441696+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-11-17T12:24:21.441705+01:00\\"}"}	\N	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key5],v=1","test::Fail[agent1,key=key2],v=1"}
4d1261c8-ddbb-4f4a-8ac6-d5be021705c1	deploy	2026-11-17 12:24:21.450116+01	2026-11-17 12:24:21.459337+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 3f859519-79cb-4aa8-b346-e765b552af6d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"3f859519-79cb-4aa8-b346-e765b552af6d\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.452745+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 3f859519-79cb-4aa8-b346-e765b552af6d) - duration: 0.0064 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0064084529876708984, \\"deploy_id\\": \\"3f859519-79cb-4aa8-b346-e765b552af6d\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.459261+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key1],v=1"}
d91e0d80-925a-4f44-bf4a-1723f080fe1d	deploy	2026-11-17 12:24:21.461111+01	2026-11-17 12:24:21.463116+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d9cefb02-6848-4504-a37a-0a9c5e389e7d).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"d9cefb02-6848-4504-a37a-0a9c5e389e7d\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.461706+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/bart/workspace/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/bart/workspace/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.462585+01:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: d9cefb02-6848-4504-a37a-0a9c5e389e7d) - duration: 0.0013 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.00133514404296875, \\"deploy_id\\": \\"d9cefb02-6848-4504-a37a-0a9c5e389e7d\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.463077+01:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Fail[agent1,key=key2],v=1"}
d777f2ed-c682-4d1b-89c3-0b297258035a	deploy	2026-11-17 12:24:21.46393+01	2026-11-17 12:24:21.46772+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 46cfe483-03ac-4f9a-ba05-ba1a9229c026).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"46cfe483-03ac-4f9a-ba05-ba1a9229c026\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.464511+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 46cfe483-03ac-4f9a-ba05-ba1a9229c026) - duration: 0.0031 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.0031147003173828125, \\"deploy_id\\": \\"46cfe483-03ac-4f9a-ba05-ba1a9229c026\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.467682+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key6],v=1"}
a42c6802-a641-4449-9015-b13412f81aa9	deploy	2026-11-17 12:24:21.469086+01	2026-11-17 12:24:21.470158+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 077636be-4bbe-491b-9290-ea7e6ee5b0d6).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"077636be-4bbe-491b-9290-ea7e6ee5b0d6\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.469810+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.470009+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 077636be-4bbe-491b-9290-ea7e6ee5b0d6) - duration: 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.000270843505859375, \\"deploy_id\\": \\"077636be-4bbe-491b-9290-ea7e6ee5b0d6\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.470128+01:00\\"}"}	skipped	\N	nochange	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key3],v=1"}
28d5d3fb-edd6-4ba5-9b27-a025fbefc778	store	2026-11-17 12:24:21.600526+01	2026-11-17 12:24:21.603883+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-11-17T12:24:21.603894+01:00\\"}"}	\N	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	2	{"test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key9],v=2","test::Fail[agent1,key=key2],v=2"}
39eea1a3-68ae-4297-ba13-d3f47157478f	dryrun	2026-11-17 12:24:21.593699+01	2026-11-17 12:24:21.594296+01	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.593859+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00032711029052734375, \\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.594270+01:00\\"}"}	dry	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Fail[agent1,key=key2],v=1"}
006b6a10-9898-4f78-9bce-8b6a2a916b70	dryrun	2026-11-17 12:24:21.599466+01	2026-11-17 12:24:21.599956+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.599560+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00028777122497558594, \\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.599925+01:00\\"}"}	dry	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key1],v=1"}
e6d285d8-8dc7-46fe-a29b-beb48717ab36	dryrun	2026-11-17 12:24:21.602136+01	2026-11-17 12:24:21.602689+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.602239+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6 - duration 0.0004 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003650188446044922, \\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.602668+01:00\\"}"}	dry	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key3],v=1"}
3daa938a-da1f-4150-ae7e-57c00404d439	dryrun	2026-11-17 12:24:21.604684+01	2026-11-17 12:24:21.605674+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.604789+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6 - duration 0.0008 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0007748603820800781, \\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.605644+01:00\\"}"}	dry	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key5],v=1"}
359563d9-99e3-4a26-9c34-6494cd8b9e96	dryrun	2026-11-17 12:24:21.610518+01	2026-11-17 12:24:21.611438+01	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.610675+01:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 4232e784-39fb-406d-be3a-697b1d2cafc6 - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006091594696044922, \\"dry_run_id\\": \\"4232e784-39fb-406d-be3a-697b1d2cafc6\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.611403+01:00\\"}"}	dry	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	1	{"test::Resource[agent1,key=key6],v=1"}
dd874e85-b52d-4a4b-a1c5-58fdb811d015	deploy	2026-11-17 12:24:21.618669+01	2026-11-17 12:24:21.643836+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 00f114b1-cb13-4632-88fa-3c3df0d53d3a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"00f114b1-cb13-4632-88fa-3c3df0d53d3a\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.635363+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 00f114b1-cb13-4632-88fa-3c3df0d53d3a) - duration: 0.0083 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.008302927017211914, \\"deploy_id\\": \\"00f114b1-cb13-4632-88fa-3c3df0d53d3a\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.643768+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	900ac41c-83ce-464d-bf86-18d9c42d800e	2	{"test::Resource[agent1,key=key9],v=2"}
783e8948-e42e-43f9-ab8d-fd8081da81cb	deploy	2026-11-17 12:24:21.646129+01	2026-11-17 12:24:21.651065+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 0cd43b77-23ba-4265-9809-f3d4d1f22f8b).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"0cd43b77-23ba-4265-9809-f3d4d1f22f8b\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.647226+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.647466+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 0cd43b77-23ba-4265-9809-f3d4d1f22f8b) - duration: 0.0037 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.003693819046020508, \\"deploy_id\\": \\"0cd43b77-23ba-4265-9809-f3d4d1f22f8b\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.651002+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	900ac41c-83ce-464d-bf86-18d9c42d800e	2	{"test::Resource[agent1,key=key11],v=2"}
509140f2-9e6a-4585-b426-3bb45daec629	store	2026-11-17 12:24:21.751989+01	2026-11-17 12:24:21.75504+01	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-11-17T12:24:21.755056+01:00\\"}"}	\N	\N	\N	900ac41c-83ce-464d-bf86-18d9c42d800e	3	{"test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key4],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key5],v=3"}
b457373e-cd46-4578-91e2-00c87a1abda9	deploy	2026-11-17 12:24:21.653889+01	2026-11-17 12:24:21.660898+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1eeababf-8a0f-43ad-b8bf-25c28278381e).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"1eeababf-8a0f-43ad-b8bf-25c28278381e\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.655003+01:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.655262+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 1eeababf-8a0f-43ad-b8bf-25c28278381e) - duration: 0.0057 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.0057332515716552734, \\"deploy_id\\": \\"1eeababf-8a0f-43ad-b8bf-25c28278381e\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.660833+01:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	900ac41c-83ce-464d-bf86-18d9c42d800e	2	{"test::Resource[agent1,key=key10],v=2"}
a3e03f70-36c4-47cf-b8cd-fddbeca2fa9f	deploy	2026-11-17 12:24:21.662527+01	2026-11-17 12:24:21.667843+01	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 87931def-2422-479d-9d1a-5299ec1bd62c).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"87931def-2422-479d-9d1a-5299ec1bd62c\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.663812+01:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 87931def-2422-479d-9d1a-5299ec1bd62c) - duration: 0.0039 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.003907918930053711, \\"deploy_id\\": \\"87931def-2422-479d-9d1a-5299ec1bd62c\\"}, \\"timestamp\\": \\"2026-11-17T12:24:21.667792+01:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	900ac41c-83ce-464d-bf86-18d9c42d800e	2	{"test::Resource[agent1,key=key7],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
c0603fc7-facf-4d01-bf2a-d04fa767ea35	e5509da7-ac73-460d-b789-9757a92a3ff2	fs::File[localhost,path=/tmp/test]	1
c0603fc7-facf-4d01-bf2a-d04fa767ea35	deb4a6f9-bb45-4271-ad6b-933be6602d3c	fs::File[localhost,path=/tmp/test]	1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	cf489afa-a1db-450a-a061-99a28580ed39	std::AgentConfig[internal,agentname=localhost]	1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	cf489afa-a1db-450a-a061-99a28580ed39	fs::File[localhost,path=/tmp/test]	1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	4a273f81-8cec-4b62-8103-ca30e46b469b	std::AgentConfig[internal,agentname=localhost]	1
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	ff96af8a-aea5-481d-8c9f-4a0f4251c6d7	fs::File[localhost,path=/tmp/test]	1
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8207c12e-fb37-40d2-bfb4-102a67fa9c24	fs::File[localhost,path=/tmp/test]	2
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7df52a6f-9b38-4613-8706-8f37b908a0f3	fs::File[localhost,path=/tmp/test]	3
c0603fc7-facf-4d01-bf2a-d04fa767ea35	7df52a6f-9b38-4613-8706-8f37b908a0f3	fs::File[localhost,path=/tmp/test_orphan]	3
c0603fc7-facf-4d01-bf2a-d04fa767ea35	6dc5c7c9-0201-4f2d-b8ec-78f35b68acdd	fs::File[localhost,path=/tmp/test_orphan]	3
c0603fc7-facf-4d01-bf2a-d04fa767ea35	59b3da42-280e-4026-adef-3d0ab0b301ec	fs::File[localhost,path=/tmp/test]	4
c0603fc7-facf-4d01-bf2a-d04fa767ea35	c2081776-b075-4ca5-b712-074edb921b89	fs::File[localhost,path=/tmp/test]	5
c0603fc7-facf-4d01-bf2a-d04fa767ea35	17d75d5b-4ee9-4e88-adfd-142b3f38f505	fs::File[localhost,path=/tmp/test]	6
c0603fc7-facf-4d01-bf2a-d04fa767ea35	931d38b2-ef00-420d-9094-9345393e4347	test::Resource[agent3,key=key3]	7
c0603fc7-facf-4d01-bf2a-d04fa767ea35	931d38b2-ef00-420d-9094-9345393e4347	fs::File[localhost,path=/tmp/test]	7
c0603fc7-facf-4d01-bf2a-d04fa767ea35	931d38b2-ef00-420d-9094-9345393e4347	test::Resource[agent2,key=key2]	7
c0603fc7-facf-4d01-bf2a-d04fa767ea35	4225041a-e482-4d1e-a6ea-3db292e2b3b5	test::Resource[agent3,key=key3]	7
c0603fc7-facf-4d01-bf2a-d04fa767ea35	2c7f3e98-b753-43a5-b4ca-74139198a1a8	test::Resource[agent2,key=key2]	7
c0603fc7-facf-4d01-bf2a-d04fa767ea35	49e4c53c-19f8-4d60-a24d-d5fb86d2abb5	test::Resource[agent2,key=key2]	8
c0603fc7-facf-4d01-bf2a-d04fa767ea35	49e4c53c-19f8-4d60-a24d-d5fb86d2abb5	fs::File[localhost,path=/tmp/test]	8
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Resource[agent1,key=key4]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Resource[agent1,key=key6]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Resource[agent1,key=key3]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Resource[agent1,key=key1]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Resource[agent1,key=key5]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	65d74dff-90c0-4ab4-a7fe-18ac128828ea	test::Fail[agent1,key=key2]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	4d1261c8-ddbb-4f4a-8ac6-d5be021705c1	test::Resource[agent1,key=key1]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	d91e0d80-925a-4f44-bf4a-1723f080fe1d	test::Fail[agent1,key=key2]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	d777f2ed-c682-4d1b-89c3-0b297258035a	test::Resource[agent1,key=key6]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	a42c6802-a641-4449-9015-b13412f81aa9	test::Resource[agent1,key=key3]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	39eea1a3-68ae-4297-ba13-d3f47157478f	test::Fail[agent1,key=key2]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	006b6a10-9898-4f78-9bce-8b6a2a916b70	test::Resource[agent1,key=key1]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	e6d285d8-8dc7-46fe-a29b-beb48717ab36	test::Resource[agent1,key=key3]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key3]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key1]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key5]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key4]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key7]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key10]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key11]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Resource[agent1,key=key9]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	28d5d3fb-edd6-4ba5-9b27-a025fbefc778	test::Fail[agent1,key=key2]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	3daa938a-da1f-4150-ae7e-57c00404d439	test::Resource[agent1,key=key5]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	359563d9-99e3-4a26-9c34-6494cd8b9e96	test::Resource[agent1,key=key6]	1
900ac41c-83ce-464d-bf86-18d9c42d800e	dd874e85-b52d-4a4b-a1c5-58fdb811d015	test::Resource[agent1,key=key9]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	783e8948-e42e-43f9-ab8d-fd8081da81cb	test::Resource[agent1,key=key11]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	b457373e-cd46-4578-91e2-00c87a1abda9	test::Resource[agent1,key=key10]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	a3e03f70-36c4-47cf-b8cd-fddbeca2fa9f	test::Resource[agent1,key=key7]	2
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key7]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key3]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key4]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Fail[agent1,key=key2]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key1]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key8]	3
900ac41c-83ce-464d-bf86-18d9c42d800e	509140f2-9e6a-4585-b426-3bb45daec629	test::Resource[agent1,key=key5]	3
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
ce83f2f0-68fb-4022-9bc9-2d6aa852879d	1
c0603fc7-facf-4d01-bf2a-d04fa767ea35	8
900ac41c-83ce-464d-bf86-18d9c42d800e	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
vedett	c0603fc7-facf-4d01-bf2a-d04fa767ea35	2026-11-17 12:23:57.811399+01	\N	b147b225-aa25-4d2f-b922-bd031bf263b8
vedett	ce83f2f0-68fb-4022-9bc9-2d6aa852879d	2026-11-17 12:23:57.947683+01	\N	9857e9a8-9021-45c9-81e6-be26013af1f9
vedett	900ac41c-83ce-464d-bf86-18d9c42d800e	2026-11-17 12:24:21.324028+01	2026-11-17 12:24:21.746923+01	46b21651-39e6-406a-bd3f-5b938624f56f
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610161,202610280,202611170}
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

--\unrestrict 1nVxfwimzFayrq4iDRacJy2A8QJsXFbZ3YmVsXSgrqoo7zT5pZ6Y7NccgkCNatj

