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
05b94f62-2b55-4bce-9e8c-d8d53833a877	$__scheduler	f	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	$__scheduler	f	\N
defb1f71-859e-4d68-bce0-c4290bdcffb5	$__scheduler	f	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	localhost	f	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	localhost	f	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	internal	f	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	agent2	f	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	agent3	f	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	agent1	t	t
dd4b4a87-db21-4eb7-b987-96cd2406ba10	$__scheduler	t	t
995ef865-d1b9-4c8b-a365-ce6ae52c1120	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
1	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
1	internal	std	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a
1	localhost	fs	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a
2	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
2	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
3	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
3	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
4	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
4	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
5	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
5	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
6	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
6	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
7	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
7	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
8	localhost	fs	05b94f62-2b55-4bce-9e8c-d8d53833a877
8	localhost	std	05b94f62-2b55-4bce-9e8c-d8d53833a877
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
33269c97-7717-4182-a23a-92bd9634d516	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:34:47.606567+02	2026-10-16 11:35:03.370827+02	2026-10-16 11:34:47.58406+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	b8ce6120-7a78-42dc-914f-445d35dc90e2	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
6315c2ab-ff68-42e7-95a6-8108ccd2cdad	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	2026-10-16 11:35:03.685521+02	2026-10-16 11:35:17.451691+02	2026-10-16 11:35:03.664233+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	4cb64546-2c07-4a03-926c-8b4948d9ce13	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
dd1550ef-9ffe-4483-9fee-1d24d9a025b6	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:17.757183+02	2026-10-16 11:35:18.686736+02	2026-10-16 11:35:17.742333+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	f890fa71-96ea-4059-948f-dfd2722e0cdf	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
d979c39d-6c79-4c0e-9fd5-d06e04e35ceb	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:18.791603+02	2026-10-16 11:35:19.7445+02	2026-10-16 11:35:18.701619+02	{}	{"add_one_resource": "true"}	t	f	t	3	8e171e7e-90cb-4c24-b728-dca744c7f7f4	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
20be098b-5d38-4d7c-89a1-9971d02868fc	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:19.849578+02	2026-10-16 11:35:20.795425+02	2026-10-16 11:35:19.768904+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	61eafafd-301b-4b96-b95f-b6456f0e4dd4	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bf37c767-b712-4559-9b56-2c1facdec17b	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:20.900084+02	2026-10-16 11:35:21.848273+02	2026-10-16 11:35:20.85656+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	37be43e5-7d9a-496c-8ca4-9fde00515976	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:21.998009+02	2026-10-16 11:35:35.493176+02	2026-10-16 11:35:21.983596+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	7f646d1d-33e6-4d9d-8e0b-e4c25b811720	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
bac39a73-5e91-4beb-bf0b-5de8a4e0b283	995ef865-d1b9-4c8b-a365-ce6ae52c1120	2026-10-16 11:35:36.507412+02	2026-10-16 11:35:36.511655+02	2026-10-16 11:35:36.492391+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	58a98efe-7258-43b9-b2ba-a2996ff758a9	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:03.348451+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:35.786164+02	t	\N	2	{}	{}	7	t	\N	\N
1	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	2026-10-16 11:35:17.435045+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:18.67797+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:19.736267+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:20.786333+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:21.839267+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:35.48155+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2026-10-16 11:35:36.066163+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:35:35.622043+02	t	\N	3	{}	{}	6	t	\N	\N
2	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2026-10-16 11:35:36.245216+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2026-10-16 11:35:36.369507+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	1	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	1	fs	1.2.0
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	std	7.0.0
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	2	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	2	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	3	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	3	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	4	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	4	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	5	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	5	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	6	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	6	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	7	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	7	std	8.7.5
05b94f62-2b55-4bce-9e8c-d8d53833a877	8	fs	1.2.0
05b94f62-2b55-4bce-9e8c-d8d53833a877	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	discovery::Discovered[myagent,name=discovered]	{}	2026-10-16 11:35:36.372928+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
05b94f62-2b55-4bce-9e8c-d8d53833a877	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-16 11:35:36.372947+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
1bb86145-8eb4-4258-b8aa-889d3d952233	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	2026-10-16 11:35:36.228581+02	6	0	{"495cb0e5-b984-5e6d-a5cc-29d119b2084b": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "5684f676-de6f-5688-a454-106a50b33bc5": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "a73d0b08-daee-5f63-a11a-a59732e6dc08": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "b87430c4-5bc4-5ba7-8ccc-32ee861767e0": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}, "c899c6ab-130a-5778-ba37-c8c6c787877a": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "fa673f48-a939-59aa-a6f3-15b4a78694a1": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
995ef865-d1b9-4c8b-a365-ce6ae52c1120	dev-4	a8070ca6-126a-48c7-ab37-c30f548f78ee			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
05b94f62-2b55-4bce-9e8c-d8d53833a877	dev-1	a8070ca6-126a-48c7-ab37-c30f548f78ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	dev-1-twin	a8070ca6-126a-48c7-ab37-c30f548f78ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
defb1f71-859e-4d68-bce0-c4290bdcffb5	dev-2	a8070ca6-126a-48c7-ab37-c30f548f78ee			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
dd4b4a87-db21-4eb7-b987-96cd2406ba10	dev-3	a8070ca6-126a-48c7-ab37-c30f548f78ee			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	05b94f62-2b55-4bce-9e8c-d8d53833a877	{}	f
fs	1.2.0	05b94f62-2b55-4bce-9e8c-d8d53833a877	{}	f
std	7.0.0	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	{}	f
fs	1.2.0	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	{}	f
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
254ea635-c26a-41cd-b247-89d9385532b4	995ef865-d1b9-4c8b-a365-ce6ae52c1120	2026-10-16 11:35:36.513119+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/bac39a73-5e91-4beb-bf0b-5de8a4e0b283	f	f	bac39a73-5e91-4beb-bf0b-5de8a4e0b283
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
a7c9c12d-6c91-499a-947b-eb8a9ba8dd6e	fact1	value1	05b94f62-2b55-4bce-9e8c-d8d53833a877	std::testing::NullResource[localhost,name=test1]	fact	2026-10-16 11:35:20.841328+02	{}	f
b517c736-fafa-4147-9ba1-1d9b37f6dcfd	fact2	value2	05b94f62-2b55-4bce-9e8c-d8d53833a877	std::testing::NullResource[localhost,name=test2]	fact	2026-10-16 11:35:20.844502+02	{}	t
c0843281-9584-4f6b-b906-802a0e7b661e	fact3	value3	05b94f62-2b55-4bce-9e8c-d8d53833a877	std::testing::NullResource[localhost,name=test3]	fact	2026-10-16 11:35:20.847104+02	{}	t
5498953d-c3fa-477d-b789-bf1797ae8e40	parameter1	value1	05b94f62-2b55-4bce-9e8c-d8d53833a877		fact	2026-10-16 11:35:20.849694+02	{}	f
91f6289a-87fd-4c86-afcc-3087f374e6fe	parameter2	value2	05b94f62-2b55-4bce-9e8c-d8d53833a877		fact	2026-10-16 11:35:20.852155+02	{}	f
3f7ea255-9947-4136-af30-f9a3d0d18639	parameter3	value3	05b94f62-2b55-4bce-9e8c-d8d53833a877		fact	2026-10-16 11:35:20.854416+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
a8070ca6-126a-48c7-ab37-c30f548f78ee	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
60315f82-c5bd-4825-a400-c038cb07fc40	2026-10-16 11:34:47.608004+02	2026-10-16 11:34:47.617169+02		Init		Using extra environment variables during compile \n	0	33269c97-7717-4182-a23a-92bd9634d516
371742a3-b73c-44e9-a6ae-63576402cb9d	2026-10-16 11:34:47.618955+02	2026-10-16 11:34:47.6506+02		Venv check		Creating new venv at /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env-py3.14\n	0	33269c97-7717-4182-a23a-92bd9634d516
0c129730-e6b8-4071-887b-78b75fd803de	2026-10-16 11:34:47.654583+02	2026-10-16 11:34:48.015115+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	33269c97-7717-4182-a23a-92bd9634d516
0e2d0eb6-c0d5-4178-ad49-47beabef33ca	2026-10-16 11:34:48.016067+02	2026-10-16 11:35:02.385618+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpg2kon06j:\n                                 Pip command: /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpg2kon06j inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Downloading more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Downloading strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, more-itertools, mitogen, jsonpath-ng, strawberry-graphql, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.10.1 mitogen-0.3.54 more-itertools-11.2.1 strawberry-graphql-0.335.0 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	33269c97-7717-4182-a23a-92bd9634d516
75b9bc67-8a8a-4e15-9679-0bbdc9b54456	2026-10-16 11:35:03.729293+02	2026-10-16 11:35:04.074344+02	/tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	6315c2ab-ff68-42e7-95a6-8108ccd2cdad
fd3a22e3-7d9e-4599-b900-28a5ab74a886	2026-10-16 11:35:18.79327+02	2026-10-16 11:35:18.803281+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	d979c39d-6c79-4c0e-9fd5-d06e04e35ceb
d356a174-4f32-4820-b593-a77c15112ac8	2026-10-16 11:35:02.386647+02	2026-10-16 11:35:03.370157+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpm562hvlk --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.019 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.027 seconds\ncompiler       DEBUG   The entire export command took 0.081 seconds\n	0	33269c97-7717-4182-a23a-92bd9634d516
312d7c1c-56bb-437f-8af0-8082257f3496	2026-10-16 11:35:18.804496+02	2026-10-16 11:35:18.809258+02		Venv check		Found existing venv\n	0	d979c39d-6c79-4c0e-9fd5-d06e04e35ceb
684cbebc-5ace-4740-af8d-d3cd02784209	2026-10-16 11:35:03.687185+02	2026-10-16 11:35:03.69473+02		Init		Using extra environment variables during compile \n	0	6315c2ab-ff68-42e7-95a6-8108ccd2cdad
110eb2cd-a265-45b4-af92-601a0ecca730	2026-10-16 11:35:03.696128+02	2026-10-16 11:35:03.725964+02		Venv check		Creating new venv at /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env-py3.14\n	0	6315c2ab-ff68-42e7-95a6-8108ccd2cdad
2ce277fb-9270-4c69-8ff0-ea0fe95a9a74	2026-10-16 11:35:17.758354+02	2026-10-16 11:35:17.763375+02		Init		Using extra environment variables during compile \n	0	dd1550ef-9ffe-4483-9fee-1d24d9a025b6
1dc661bb-44b5-4c5d-ae5e-b27dabfc25cb	2026-10-16 11:35:17.763616+02	2026-10-16 11:35:17.764+02		Venv check		Found existing venv\n	0	dd1550ef-9ffe-4483-9fee-1d24d9a025b6
a36ca270-3bc0-4f98-bfee-d29f48ffadcf	2026-10-16 11:35:04.075097+02	2026-10-16 11:35:16.504198+02	/tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpmcu8dqg_:\n                                 Pip command: /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpmcu8dqg_ inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, more-itertools, mitogen, jsonpath-ng, strawberry-graphql, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.10.1 mitogen-0.3.54 more-itertools-11.2.1 strawberry-graphql-0.335.0 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	6315c2ab-ff68-42e7-95a6-8108ccd2cdad
f4f45ef3-e309-4751-8a08-76051e61e461	2026-10-16 11:35:16.50547+02	2026-10-16 11:35:17.451091+02	/tmp/tmpudc5a8lt/server/e0a0b8fa-1d92-4eba-8a38-e1786b5b116a/compiler/.env/bin/python -m inmanta.app -vvv export -X -e e0a0b8fa-1d92-4eba-8a38-e1786b5b116a --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpcwdwwnp3 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.018 seconds\ncompiler       DEBUG   The entire export command took 0.058 seconds\n	0	6315c2ab-ff68-42e7-95a6-8108ccd2cdad
bf996850-1d5f-4677-a5bf-f323f8e9882b	2026-10-16 11:35:17.764184+02	2026-10-16 11:35:18.686281+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpxy9lkcq_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.012 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.015 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.065 seconds\n	0	dd1550ef-9ffe-4483-9fee-1d24d9a025b6
815dea3d-35a1-4f82-9cbd-c7c796eb725c	2026-10-16 11:35:18.810325+02	2026-10-16 11:35:19.744087+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmp5oryuov_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	d979c39d-6c79-4c0e-9fd5-d06e04e35ceb
93098d4a-4099-434c-aa19-1481409a3541	2026-10-16 11:35:19.851652+02	2026-10-16 11:35:19.8611+02		Init		Using extra environment variables during compile \n	0	20be098b-5d38-4d7c-89a1-9971d02868fc
eb03f7ef-a31f-452d-bccd-b49658fc629c	2026-10-16 11:35:19.862217+02	2026-10-16 11:35:19.864197+02		Venv check		Found existing venv\n	0	20be098b-5d38-4d7c-89a1-9971d02868fc
799581ea-abdc-4df1-8d76-df847b561759	2026-10-16 11:35:19.865273+02	2026-10-16 11:35:20.794977+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpe4_036uh --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	20be098b-5d38-4d7c-89a1-9971d02868fc
44e1d45d-8889-4ec8-8e88-2a8796064a37	2026-10-16 11:35:20.902009+02	2026-10-16 11:35:20.910932+02		Init		Using extra environment variables during compile \n	0	bf37c767-b712-4559-9b56-2c1facdec17b
a691c77f-8a31-4f78-8872-58c6c935a4ee	2026-10-16 11:35:20.911961+02	2026-10-16 11:35:20.913743+02		Venv check		Found existing venv\n	0	bf37c767-b712-4559-9b56-2c1facdec17b
268623b4-6532-4b9b-8907-601179b3ad96	2026-10-16 11:35:22.012976+02	2026-10-16 11:35:22.357223+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b
43e9bdc5-728c-4350-b92b-a3648779291b	2026-10-16 11:35:20.914433+02	2026-10-16 11:35:21.847754+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmphlz_8w4_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.048 seconds\n	0	bf37c767-b712-4559-9b56-2c1facdec17b
178ec09f-20e8-4fd7-b29e-71c76a82805e	2026-10-16 11:35:21.99903+02	2026-10-16 11:35:22.006099+02		Init		Using extra environment variables during compile \n	0	b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b
e6520901-8c35-46e6-9acf-dc813f614766	2026-10-16 11:35:22.007053+02	2026-10-16 11:35:22.009093+02		Venv check		Found existing venv\n	0	b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b
1aa50e20-a7af-4e67-ad92-24ee4c3abd76	2026-10-16 11:35:22.357968+02	2026-10-16 11:35:34.594154+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpt3u7yvlk:\n                                 Pip command: /tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpt3u7yvlk inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.335.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b
7473bc0d-ee47-4ebb-992d-aa01d016529d	2026-10-16 11:35:34.594909+02	2026-10-16 11:35:35.492641+02	/tmp/tmpudc5a8lt/server/05b94f62-2b55-4bce-9e8c-d8d53833a877/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 05b94f62-2b55-4bce-9e8c-d8d53833a877 --server_address localhost --server_port 42543 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp2m0uuznt --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:42543/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:42543/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	b72bfcdc-65bc-450d-9a9b-ac8f9ea6c42b
bb44cf7e-6406-4334-9545-6c8cc3d734fe	2026-10-16 11:35:36.509222+02	2026-10-16 11:35:36.51136+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpudc5a8lt/server/995ef865-d1b9-4c8b-a365-ce6ae52c1120/compiler and no repository set.\n	1	bac39a73-5e91-4beb-bf0b-5de8a4e0b283
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	84ea0787-4bb1-4ee2-8254-4cf9172c072b
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	7450e689-3899-4ff8-bae8-91ffe3e3cf9b
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7450e689-3899-4ff8-bae8-91ffe3e3cf9b
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a2cedf44-7eaf-484f-a5e9-6c398d27e6a2
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	bb483e33-64a3-407e-a7d0-5564ff3e3ac8
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	bb483e33-64a3-407e-a7d0-5564ff3e3ac8
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	13b82864-4fcb-4875-bf2f-c9ab620f4057
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	a0e08f69-5a0d-426d-b770-6064e5647fe0
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7805b606-9593-49d2-8c14-a24c53de131d
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e0d78ab4-f6d9-486d-99ff-f62aa641262a
05b94f62-2b55-4bce-9e8c-d8d53833a877	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	a5ad3929-672b-4c6d-881d-b840fc2eb081
05b94f62-2b55-4bce-9e8c-d8d53833a877	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	d4d4580e-aded-45fb-bad2-db77620f2b0e
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	54b307c6-06e2-4015-96bc-37469888d678
05b94f62-2b55-4bce-9e8c-d8d53833a877	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	60a0d50a-16be-47e0-9a34-7908ea217449
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	b3e38683-eca7-48cf-9a38-166be96f1298
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	b3e38683-eca7-48cf-9a38-166be96f1298
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
9e39fb44-f95e-4392-8c05-e3eaea9f83c6	dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-16 11:35:36.319337+02
f5f6b73c-0eb4-4095-aeb4-ab41b3ca40eb	dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-16 11:35:36.356958+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-16 11:35:36.089469+02	\N	\N	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test]	2026-10-16 11:35:03.542194+02	\N	2026-10-16 11:35:03.542194+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:03.505389+02	f	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key1]	2026-10-16 11:35:36.107269+02	2026-10-16 11:35:36.094106+02	2026-10-16 11:35:36.107269+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.089469+02	t	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key7]	2026-10-16 11:35:36.337169+02	2026-10-16 11:35:36.325566+02	2026-10-16 11:35:36.337169+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.253377+02	t	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Fail[agent1,key=key2]	2026-10-16 11:35:36.11025+02	\N	2026-10-16 11:35:36.11025+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:36.089469+02	f	\N	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	std::AgentConfig[internal,agentname=localhost]	2026-10-16 11:35:17.619835+02	\N	2026-10-16 11:35:17.619835+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:17.589051+02	f	\N	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	fs::File[localhost,path=/tmp/test]	2026-10-16 11:35:17.624549+02	\N	2026-10-16 11:35:17.624549+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:17.589051+02	f	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key9]	2026-10-16 11:35:36.352929+02	2026-10-16 11:35:36.340981+02	2026-10-16 11:35:36.352929+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.253377+02	t	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key3]	2026-10-16 11:35:36.115876+02	\N	2026-10-16 11:35:36.115876+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-16 11:35:36.089469+02	f	\N	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	fs::File[localhost,path=/tmp/test_orphan]	2026-10-16 11:35:19.766206+02	\N	2026-10-16 11:35:19.766206+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:19.761297+02	f	\N	3
05b94f62-2b55-4bce-9e8c-d8d53833a877	test::Resource[agent2,key=key2]	2026-10-16 11:35:35.653067+02	\N	2026-10-16 11:35:35.653067+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:35.646967+02	f	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key11]	2026-10-16 11:35:36.356958+02	\N	2026-10-16 11:35:36.356958+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.253377+02	f	f5f6b73c-0eb4-4095-aeb4-ab41b3ca40eb	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	test::Resource[agent3,key=key3]	2026-10-16 11:35:35.654958+02	\N	2026-10-16 11:35:35.654958+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:35:35.646967+02	f	\N	7
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-16 11:35:36.089469+02	\N	\N	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key6]	2026-10-16 11:35:36.114234+02	2026-10-16 11:35:36.111111+02	2026-10-16 11:35:36.114234+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.089469+02	t	\N	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	test::Resource[agent1,key=key10]	2026-10-16 11:35:36.319337+02	\N	2026-10-16 11:35:36.319337+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:35:36.253377+02	f	9e39fb44-f95e-4392-8c05-e3eaea9f83c6	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	84ea0787-4bb1-4ee2-8254-4cf9172c072b	\N
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	7450e689-3899-4ff8-bae8-91ffe3e3cf9b	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	a2cedf44-7eaf-484f-a5e9-6c398d27e6a2	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	bb483e33-64a3-407e-a7d0-5564ff3e3ac8	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	13b82864-4fcb-4875-bf2f-c9ab620f4057	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	a0e08f69-5a0d-426d-b770-6064e5647fe0	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	7805b606-9593-49d2-8c14-a24c53de131d	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	e0d78ab4-f6d9-486d-99ff-f62aa641262a	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	a5ad3929-672b-4c6d-881d-b840fc2eb081	set-a
05b94f62-2b55-4bce-9e8c-d8d53833a877	d4d4580e-aded-45fb-bad2-db77620f2b0e	set-b
05b94f62-2b55-4bce-9e8c-d8d53833a877	54b307c6-06e2-4015-96bc-37469888d678	\N
05b94f62-2b55-4bce-9e8c-d8d53833a877	60a0d50a-16be-47e0-9a34-7908ea217449	set-a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	4d7533f4-6fa9-4302-b982-86570449a44b	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	58177485-5127-42c4-8734-e61506b9a62a	\N
dd4b4a87-db21-4eb7-b987-96cd2406ba10	b3e38683-eca7-48cf-9a38-166be96f1298	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	1	84ea0787-4bb1-4ee2-8254-4cf9172c072b
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	7450e689-3899-4ff8-bae8-91ffe3e3cf9b
05b94f62-2b55-4bce-9e8c-d8d53833a877	2	a2cedf44-7eaf-484f-a5e9-6c398d27e6a2
05b94f62-2b55-4bce-9e8c-d8d53833a877	3	bb483e33-64a3-407e-a7d0-5564ff3e3ac8
05b94f62-2b55-4bce-9e8c-d8d53833a877	4	13b82864-4fcb-4875-bf2f-c9ab620f4057
05b94f62-2b55-4bce-9e8c-d8d53833a877	5	a0e08f69-5a0d-426d-b770-6064e5647fe0
05b94f62-2b55-4bce-9e8c-d8d53833a877	6	7805b606-9593-49d2-8c14-a24c53de131d
05b94f62-2b55-4bce-9e8c-d8d53833a877	7	e0d78ab4-f6d9-486d-99ff-f62aa641262a
05b94f62-2b55-4bce-9e8c-d8d53833a877	7	a5ad3929-672b-4c6d-881d-b840fc2eb081
05b94f62-2b55-4bce-9e8c-d8d53833a877	7	d4d4580e-aded-45fb-bad2-db77620f2b0e
05b94f62-2b55-4bce-9e8c-d8d53833a877	8	54b307c6-06e2-4015-96bc-37469888d678
05b94f62-2b55-4bce-9e8c-d8d53833a877	8	60a0d50a-16be-47e0-9a34-7908ea217449
dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	4d7533f4-6fa9-4302-b982-86570449a44b
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	58177485-5127-42c4-8734-e61506b9a62a
dd4b4a87-db21-4eb7-b987-96cd2406ba10	3	b3e38683-eca7-48cf-9a38-166be96f1298
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
a79dafae-2046-425c-ae30-cdf1f606114d	store	2026-10-16 11:35:03.348357+02	2026-10-16 11:35:03.35829+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:35:03.358306+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	1	{"fs::File[localhost,path=/tmp/test],v=1"}
41957a63-c799-4b70-86ee-58f95c68d834	deploy	2026-10-16 11:35:03.531555+02	2026-10-16 11:35:03.542194+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:03.541454+02:00\\"}"}	unavailable	\N	nochange	05b94f62-2b55-4bce-9e8c-d8d53833a877	1	{"fs::File[localhost,path=/tmp/test],v=1"}
89572e9f-2cbb-4451-936e-e0846fb90990	store	2026-10-16 11:35:17.434972+02	2026-10-16 11:35:17.443569+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:35:17.443580+02:00\\"}"}	\N	\N	\N	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
6fc7b923-7781-4f89-8f60-52da05462689	deploy	2026-10-16 11:35:17.612155+02	2026-10-16 11:35:17.619835+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:17.619312+02:00\\"}"}	unavailable	\N	nochange	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
d93124e4-75af-458e-9374-d96a19dbb41f	deploy	2026-10-16 11:35:17.623453+02	2026-10-16 11:35:17.624549+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:17.624128+02:00\\"}"}	unavailable	\N	nochange	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1	{"fs::File[localhost,path=/tmp/test],v=1"}
5f87f4f9-06a8-44da-bd26-d1f131d98f39	store	2026-10-16 11:35:18.677922+02	2026-10-16 11:35:18.680017+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-16T11:35:18.680025+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	2	{"fs::File[localhost,path=/tmp/test],v=2"}
95767e1f-0a46-4aee-b1ec-c285e036284e	store	2026-10-16 11:35:19.736219+02	2026-10-16 11:35:19.738196+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-16T11:35:19.738205+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
9b11554e-3f14-45ef-a6d0-15ea42579f9d	deploy	2026-10-16 11:35:19.764309+02	2026-10-16 11:35:19.766206+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-16T11:35:19.765734+02:00\\"}"}	unavailable	\N	nochange	05b94f62-2b55-4bce-9e8c-d8d53833a877	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
60792d22-a950-4b6c-96ab-7786ff3d44a7	store	2026-10-16 11:35:20.786285+02	2026-10-16 11:35:20.788105+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-16T11:35:20.788113+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	4	{"fs::File[localhost,path=/tmp/test],v=4"}
ba6e9921-d299-4760-b88b-853f675b1ec8	store	2026-10-16 11:35:21.839218+02	2026-10-16 11:35:21.840983+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-16T11:35:21.840992+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	5	{"fs::File[localhost,path=/tmp/test],v=5"}
36b50a4e-d9b7-46d6-99c4-d65d622e4303	store	2026-10-16 11:35:35.481498+02	2026-10-16 11:35:35.4844+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-16T11:35:35.484409+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	6	{"fs::File[localhost,path=/tmp/test],v=6"}
64514859-d175-43a7-8406-891f366ce53f	store	2026-10-16 11:35:35.621947+02	2026-10-16 11:35:35.625914+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-16T11:35:35.625921+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	7	{"test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7","fs::File[localhost,path=/tmp/test],v=7"}
188ecd39-e0b9-4f4c-88aa-76103942c906	deploy	2026-10-16 11:35:35.651693+02	2026-10-16 11:35:35.653067+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-16T11:35:35.652532+02:00\\"}"}	unavailable	\N	nochange	05b94f62-2b55-4bce-9e8c-d8d53833a877	7	{"test::Resource[agent2,key=key2],v=7"}
50678e0e-a2a2-464a-bda0-dcf0e69110f7	deploy	2026-10-16 11:35:35.653125+02	2026-10-16 11:35:35.654958+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-16T11:35:35.654492+02:00\\"}"}	unavailable	\N	nochange	05b94f62-2b55-4bce-9e8c-d8d53833a877	7	{"test::Resource[agent3,key=key3],v=7"}
19883032-4238-4652-9463-c006d9250587	store	2026-10-16 11:35:35.785827+02	2026-10-16 11:35:35.802194+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-16T11:35:35.802223+02:00\\"}"}	\N	\N	\N	05b94f62-2b55-4bce-9e8c-d8d53833a877	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
98db1809-188e-4b57-9eaf-2b9d4ef93328	store	2026-10-16 11:35:36.06586+02	2026-10-16 11:35:36.083946+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:35:36.083971+02:00\\"}"}	\N	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key4],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key3],v=1"}
24f82360-14b7-46e6-a4e1-fb1de97604b8	deploy	2026-10-16 11:35:36.094149+02	2026-10-16 11:35:36.107269+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1bb63da5-5c60-440f-8b45-b88689ef4674).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"1bb63da5-5c60-440f-8b45-b88689ef4674\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.102187+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 1bb63da5-5c60-440f-8b45-b88689ef4674) - duration: 0.0050 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.0049877166748046875, \\"deploy_id\\": \\"1bb63da5-5c60-440f-8b45-b88689ef4674\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.107230+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key1],v=1"}
83328c5a-a365-46ac-ae2b-05bf01d63abd	deploy	2026-10-16 11:35:36.108451+02	2026-10-16 11:35:36.11025+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: b3c15109-2f22-4350-9581-cdba2b942f59).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"b3c15109-2f22-4350-9581-cdba2b942f59\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.109137+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.109738+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: b3c15109-2f22-4350-9581-cdba2b942f59) - duration: 0.0011 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0010526180267333984, \\"deploy_id\\": \\"b3c15109-2f22-4350-9581-cdba2b942f59\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.110225+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Fail[agent1,key=key2],v=1"}
fb4ad8e7-b681-48c0-8cba-d0ed4a68fb9d	deploy	2026-10-16 11:35:36.11114+02	2026-10-16 11:35:36.114234+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 349fd5b7-124e-45ae-b958-a7f69566a0ed).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"349fd5b7-124e-45ae-b958-a7f69566a0ed\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.111774+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 349fd5b7-124e-45ae-b958-a7f69566a0ed) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.002391338348388672, \\"deploy_id\\": \\"349fd5b7-124e-45ae-b958-a7f69566a0ed\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.114205+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key6],v=1"}
02d8539d-7944-402c-b01c-d9d8db2b41e7	deploy	2026-10-16 11:35:36.115005+02	2026-10-16 11:35:36.115876+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d86d54b0-8454-464f-b914-5adbf3fc2822).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"d86d54b0-8454-464f-b914-5adbf3fc2822\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.115649+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.115777+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: d86d54b0-8454-464f-b914-5adbf3fc2822) - duration: 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.00016951560974121094, \\"deploy_id\\": \\"d86d54b0-8454-464f-b914-5adbf3fc2822\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.115854+02:00\\"}"}	skipped	\N	nochange	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key3],v=1"}
235434dc-5ca2-45db-a40f-f1a399929d8c	dryrun	2026-10-16 11:35:36.236718+02	2026-10-16 11:35:36.237098+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.236772+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233 - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0002663135528564453, \\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.237084+02:00\\"}"}	dry	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Fail[agent1,key=key2],v=1"}
6d46cc0d-1a0e-4aea-bd13-20951a9dab46	store	2026-10-16 11:35:36.245102+02	2026-10-16 11:35:36.2508+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-16T11:35:36.250806+02:00\\"}"}	\N	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	{"test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key5],v=2"}
2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	store	2026-10-16 11:35:36.369459+02	2026-10-16 11:35:36.3712+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-16T11:35:36.371207+02:00\\"}"}	\N	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	3	{"test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key7],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key3],v=3"}
4e48d410-41b1-430b-9999-47281f03f60b	dryrun	2026-10-16 11:35:36.241462+02	2026-10-16 11:35:36.241728+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.241504+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00017118453979492188, \\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.241714+02:00\\"}"}	dry	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key1],v=1"}
441780a5-92fa-49eb-ad24-3ba7b083953c	dryrun	2026-10-16 11:35:36.244702+02	2026-10-16 11:35:36.244971+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.244746+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00017595291137695312, \\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.244958+02:00\\"}"}	dry	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key3],v=1"}
6625ab5e-a0e2-44d6-b259-66019dc08fc4	dryrun	2026-10-16 11:35:36.247021+02	2026-10-16 11:35:36.24728+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.247062+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00017571449279785156, \\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.247270+02:00\\"}"}	dry	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key5],v=1"}
21157caf-3376-4afc-9cfd-656d9f13af1f	dryrun	2026-10-16 11:35:36.24881+02	2026-10-16 11:35:36.249061+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.248850+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 1bb86145-8eb4-4258-b8aa-889d3d952233 - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00016355514526367188, \\"dry_run_id\\": \\"1bb86145-8eb4-4258-b8aa-889d3d952233\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.249048+02:00\\"}"}	dry	\N	\N	dd4b4a87-db21-4eb7-b987-96cd2406ba10	1	{"test::Resource[agent1,key=key6],v=1"}
74159217-0c86-4c1c-a762-363ea8279559	deploy	2026-10-16 11:35:36.299097+02	2026-10-16 11:35:36.319337+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 13028019-d215-4a1d-84df-2229f8f4ffd9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"13028019-d215-4a1d-84df-2229f8f4ffd9\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.306473+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.307068+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: 13028019-d215-4a1d-84df-2229f8f4ffd9) - duration: 0.0126 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.012589216232299805, \\"deploy_id\\": \\"13028019-d215-4a1d-84df-2229f8f4ffd9\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.319224+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	{"test::Resource[agent1,key=key10],v=2"}
59a74328-e4c3-4cf0-8600-697461234744	deploy	2026-10-16 11:35:36.325677+02	2026-10-16 11:35:36.337169+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 7774ab8c-23bb-4ac2-98af-af9fe941d24e).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"7774ab8c-23bb-4ac2-98af-af9fe941d24e\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.328585+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: 7774ab8c-23bb-4ac2-98af-af9fe941d24e) - duration: 0.0083 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.008327484130859375, \\"deploy_id\\": \\"7774ab8c-23bb-4ac2-98af-af9fe941d24e\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.337068+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	{"test::Resource[agent1,key=key7],v=2"}
d9c8cb06-c9ad-45e5-8ada-b9a1ec4f93a0	deploy	2026-10-16 11:35:36.341076+02	2026-10-16 11:35:36.352929+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: d670e212-fd29-4f74-843e-3e33e5310bbd).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"d670e212-fd29-4f74-843e-3e33e5310bbd\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.343831+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: d670e212-fd29-4f74-843e-3e33e5310bbd) - duration: 0.0089 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.008860349655151367, \\"deploy_id\\": \\"d670e212-fd29-4f74-843e-3e33e5310bbd\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.352832+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	{"test::Resource[agent1,key=key9],v=2"}
a055546b-ad23-477b-b453-6e4c31991742	deploy	2026-10-16 11:35:36.354076+02	2026-10-16 11:35:36.356958+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 82f394d8-812d-4359-8657-b10b93573a3f).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"82f394d8-812d-4359-8657-b10b93573a3f\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.354658+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.354825+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 82f394d8-812d-4359-8657-b10b93573a3f) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.002232074737548828, \\"deploy_id\\": \\"82f394d8-812d-4359-8657-b10b93573a3f\\"}, \\"timestamp\\": \\"2026-10-16T11:35:36.356930+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2	{"test::Resource[agent1,key=key11],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
05b94f62-2b55-4bce-9e8c-d8d53833a877	a79dafae-2046-425c-ae30-cdf1f606114d	fs::File[localhost,path=/tmp/test]	1
05b94f62-2b55-4bce-9e8c-d8d53833a877	41957a63-c799-4b70-86ee-58f95c68d834	fs::File[localhost,path=/tmp/test]	1
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	89572e9f-2cbb-4451-936e-e0846fb90990	std::AgentConfig[internal,agentname=localhost]	1
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	89572e9f-2cbb-4451-936e-e0846fb90990	fs::File[localhost,path=/tmp/test]	1
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	6fc7b923-7781-4f89-8f60-52da05462689	std::AgentConfig[internal,agentname=localhost]	1
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	d93124e4-75af-458e-9374-d96a19dbb41f	fs::File[localhost,path=/tmp/test]	1
05b94f62-2b55-4bce-9e8c-d8d53833a877	5f87f4f9-06a8-44da-bd26-d1f131d98f39	fs::File[localhost,path=/tmp/test]	2
05b94f62-2b55-4bce-9e8c-d8d53833a877	95767e1f-0a46-4aee-b1ec-c285e036284e	fs::File[localhost,path=/tmp/test_orphan]	3
05b94f62-2b55-4bce-9e8c-d8d53833a877	95767e1f-0a46-4aee-b1ec-c285e036284e	fs::File[localhost,path=/tmp/test]	3
05b94f62-2b55-4bce-9e8c-d8d53833a877	9b11554e-3f14-45ef-a6d0-15ea42579f9d	fs::File[localhost,path=/tmp/test_orphan]	3
05b94f62-2b55-4bce-9e8c-d8d53833a877	60792d22-a950-4b6c-96ab-7786ff3d44a7	fs::File[localhost,path=/tmp/test]	4
05b94f62-2b55-4bce-9e8c-d8d53833a877	ba6e9921-d299-4760-b88b-853f675b1ec8	fs::File[localhost,path=/tmp/test]	5
05b94f62-2b55-4bce-9e8c-d8d53833a877	36b50a4e-d9b7-46d6-99c4-d65d622e4303	fs::File[localhost,path=/tmp/test]	6
05b94f62-2b55-4bce-9e8c-d8d53833a877	64514859-d175-43a7-8406-891f366ce53f	test::Resource[agent2,key=key2]	7
05b94f62-2b55-4bce-9e8c-d8d53833a877	64514859-d175-43a7-8406-891f366ce53f	test::Resource[agent3,key=key3]	7
05b94f62-2b55-4bce-9e8c-d8d53833a877	64514859-d175-43a7-8406-891f366ce53f	fs::File[localhost,path=/tmp/test]	7
05b94f62-2b55-4bce-9e8c-d8d53833a877	188ecd39-e0b9-4f4c-88aa-76103942c906	test::Resource[agent2,key=key2]	7
05b94f62-2b55-4bce-9e8c-d8d53833a877	50678e0e-a2a2-464a-bda0-dcf0e69110f7	test::Resource[agent3,key=key3]	7
05b94f62-2b55-4bce-9e8c-d8d53833a877	19883032-4238-4652-9463-c006d9250587	test::Resource[agent2,key=key2]	8
05b94f62-2b55-4bce-9e8c-d8d53833a877	19883032-4238-4652-9463-c006d9250587	fs::File[localhost,path=/tmp/test]	8
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Resource[agent1,key=key4]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Fail[agent1,key=key2]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Resource[agent1,key=key1]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Resource[agent1,key=key5]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Resource[agent1,key=key6]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	98db1809-188e-4b57-9eaf-2b9d4ef93328	test::Resource[agent1,key=key3]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	24f82360-14b7-46e6-a4e1-fb1de97604b8	test::Resource[agent1,key=key1]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	83328c5a-a365-46ac-ae2b-05bf01d63abd	test::Fail[agent1,key=key2]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	fb4ad8e7-b681-48c0-8cba-d0ed4a68fb9d	test::Resource[agent1,key=key6]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	02d8539d-7944-402c-b01c-d9d8db2b41e7	test::Resource[agent1,key=key3]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	235434dc-5ca2-45db-a40f-f1a399929d8c	test::Fail[agent1,key=key2]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	4e48d410-41b1-430b-9999-47281f03f60b	test::Resource[agent1,key=key1]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	441780a5-92fa-49eb-ad24-3ba7b083953c	test::Resource[agent1,key=key3]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6625ab5e-a0e2-44d6-b259-66019dc08fc4	test::Resource[agent1,key=key5]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	21157caf-3376-4afc-9cfd-656d9f13af1f	test::Resource[agent1,key=key6]	1
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Fail[agent1,key=key2]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key4]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key9]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key11]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key7]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key10]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key1]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key3]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	6d46cc0d-1a0e-4aea-bd13-20951a9dab46	test::Resource[agent1,key=key5]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	74159217-0c86-4c1c-a762-363ea8279559	test::Resource[agent1,key=key10]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	59a74328-e4c3-4cf0-8600-697461234744	test::Resource[agent1,key=key7]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	d9c8cb06-c9ad-45e5-8ada-b9a1ec4f93a0	test::Resource[agent1,key=key9]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	a055546b-ad23-477b-b453-6e4c31991742	test::Resource[agent1,key=key11]	2
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key1]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key8]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key5]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key4]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key7]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Fail[agent1,key=key2]	3
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2fdef082-cd9d-4af7-b0e6-ccae55fc01b0	test::Resource[agent1,key=key3]	3
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
e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	1
05b94f62-2b55-4bce-9e8c-d8d53833a877	8
dd4b4a87-db21-4eb7-b987-96cd2406ba10	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	05b94f62-2b55-4bce-9e8c-d8d53833a877	2026-10-16 11:34:47.281748+02	\N	e0d7a742-db3e-44d2-8fca-09c6de7665c7
hugo-Latitude-5421	e0a0b8fa-1d92-4eba-8a38-e1786b5b116a	2026-10-16 11:34:47.416543+02	\N	2b40f54a-3531-4704-afd8-9f186d23771a
hugo-Latitude-5421	dd4b4a87-db21-4eb7-b987-96cd2406ba10	2026-10-16 11:35:35.924881+02	2026-10-16 11:35:36.365436+02	02343a51-e8b6-4076-a5a6-6490580f904f
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160}
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

