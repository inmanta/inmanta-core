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
    inmanta_module_version character varying NOT NULL,
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
3ded2c33-fe96-4c24-a257-d672eb577609	$__scheduler	f	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	$__scheduler	f	\N
580779f3-fb85-41d7-be0e-cfb15968d7f2	$__scheduler	f	\N
3ded2c33-fe96-4c24-a257-d672eb577609	localhost	f	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	internal	f	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	localhost	f	\N
3ded2c33-fe96-4c24-a257-d672eb577609	agent3	f	\N
3ded2c33-fe96-4c24-a257-d672eb577609	agent2	f	\N
065285aa-140b-49d3-bae9-380fef7e0573	agent1	t	t
065285aa-140b-49d3-bae9-380fef7e0573	$__scheduler	t	t
cf296431-1efb-4808-b601-c9ecc19cadca	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
1	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
1	internal	std	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58
1	localhost	fs	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58
2	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
2	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
3	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
3	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
4	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
4	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
5	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
5	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
6	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
6	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
7	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
7	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
8	localhost	fs	3ded2c33-fe96-4c24-a257-d672eb577609
8	localhost	std	3ded2c33-fe96-4c24-a257-d672eb577609
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
64027952-7eef-4a4f-b1fb-4682268d39a5	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:36:43.429326+02	2026-10-16 11:36:57.495115+02	2026-10-16 11:36:43.408518+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	c74c7a99-e28d-4b7a-8ba2-6e36bba35bf7	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
db6aea8a-6dcd-49de-89b4-e3aaa84b84a6	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	2026-10-16 11:36:57.751007+02	2026-10-16 11:37:13.371683+02	2026-10-16 11:36:57.733266+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	087ca6db-7b98-425f-b06a-f44e76788b14	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c97b0f51-e9fc-4a2a-a080-f21e75b14d94	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:13.633744+02	2026-10-16 11:37:14.643511+02	2026-10-16 11:37:13.61734+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	d144f33c-84df-4bd9-b37a-47ff24120c5e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
f58a35e7-c51d-4035-b751-3d6dd7108bc4	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:14.747751+02	2026-10-16 11:37:15.741439+02	2026-10-16 11:37:14.683891+02	{}	{"add_one_resource": "true"}	t	f	t	3	d9e8a845-3c01-4acb-bac7-c17422c9ad2d	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
33d06477-9ced-4495-87dc-cfe111e4df00	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:16.048952+02	2026-10-16 11:37:17.138212+02	2026-10-16 11:37:16.036184+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	2a207da3-ffe1-4a0f-8aab-4352b4de922b	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
27592b0c-4cfd-4555-990e-bc2817e26141	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:17.307761+02	2026-10-16 11:37:18.29155+02	2026-10-16 11:37:17.303972+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	6010454d-0f39-4048-9c5c-fb0539c0d20c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
aeac872f-c2fe-43cd-b170-ff0bcd36192c	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:18.43678+02	2026-10-16 11:37:37.804118+02	2026-10-16 11:37:18.426694+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	39038b35-50c5-41c7-a809-0f93c72c3db6	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
a8386260-4d4a-44d0-a1d4-87ad9760b5a9	cf296431-1efb-4808-b601-c9ecc19cadca	2026-10-16 11:37:38.862956+02	2026-10-16 11:37:38.876253+02	2026-10-16 11:37:38.849083+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	ab41162e-c850-4c05-b17f-e5ffe2c7927d	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:36:57.471306+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
8	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:38.148836+02	t	\N	2	{}	{}	7	t	\N	\N
1	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	2026-10-16 11:37:13.356774+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:14.634141+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:15.731175+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:17.121824+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:18.274087+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:37.791111+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	1	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	065285aa-140b-49d3-bae9-380fef7e0573	2026-10-16 11:37:38.333901+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
7	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:37:37.971891+02	t	\N	3	{}	{}	6	t	\N	\N
2	065285aa-140b-49d3-bae9-380fef7e0573	2026-10-16 11:37:38.551843+02	t	\N	9	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
3	065285aa-140b-49d3-bae9-380fef7e0573	2026-10-16 11:37:38.71718+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version, extras) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	1	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	1	fs	1.2.0	{}
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	std	7.0.0	{}
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	2	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	2	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	3	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	3	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	4	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	4	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	5	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	5	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	6	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	6	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	7	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	7	std	8.7.5	{}
3ded2c33-fe96-4c24-a257-d672eb577609	8	fs	1.2.0	{}
3ded2c33-fe96-4c24-a257-d672eb577609	8	std	8.7.5	{}
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	discovery::Discovered[myagent,name=discovered]	{}	2026-10-16 11:37:38.729535+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
3ded2c33-fe96-4c24-a257-d672eb577609	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-16 11:37:38.729556+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
526203f5-d87e-4f85-99ea-fd3ddbb8946d	065285aa-140b-49d3-bae9-380fef7e0573	1	2026-10-16 11:37:38.512366+02	6	0	{"6afd54d3-0a8b-58a6-9b8b-fb57f7278382": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "8bed4d95-1c49-5f67-a0d6-3ef6f838880b": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}, "diff_status": "skipped_for_undefined"}, "ac5a964a-c650-5d0c-b68d-4c7940bd552d": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "bfe2abbf-b7a4-5630-bd7a-3cbbc50dad4a": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "c342248b-9e48-5d4e-8886-c564b6b028a0": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "d29431b1-2986-5160-b7be-baaa9716bc1f": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
cf296431-1efb-4808-b601-c9ecc19cadca	dev-4	dac8f722-9456-42aa-8a8c-4c1f9b530c26			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
3ded2c33-fe96-4c24-a257-d672eb577609	dev-1	dac8f722-9456-42aa-8a8c-4c1f9b530c26			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	dev-1-twin	dac8f722-9456-42aa-8a8c-4c1f9b530c26			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
580779f3-fb85-41d7-be0e-cfb15968d7f2	dev-2	dac8f722-9456-42aa-8a8c-4c1f9b530c26			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
065285aa-140b-49d3-bae9-380fef7e0573	dev-3	dac8f722-9456-42aa-8a8c-4c1f9b530c26			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	3ded2c33-fe96-4c24-a257-d672eb577609	{}	f
fs	1.2.0	3ded2c33-fe96-4c24-a257-d672eb577609	{}	f
std	7.0.0	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	{}	f
fs	1.2.0	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	{}	f
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
08f8d191-d2aa-47fb-a1d0-3a0afd4e968b	cf296431-1efb-4808-b601-c9ecc19cadca	2026-10-16 11:37:38.882161+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/a8386260-4d4a-44d0-a1d4-87ad9760b5a9	f	f	a8386260-4d4a-44d0-a1d4-87ad9760b5a9
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
c5156d13-0991-410b-a05b-bc41e0a9c59a	fact1	value1	3ded2c33-fe96-4c24-a257-d672eb577609	std::testing::NullResource[localhost,name=test1]	fact	2026-10-16 11:37:17.287808+02	{}	f
de3d6e33-861d-4929-9cad-4c36027ab0de	fact2	value2	3ded2c33-fe96-4c24-a257-d672eb577609	std::testing::NullResource[localhost,name=test2]	fact	2026-10-16 11:37:17.293159+02	{}	t
3b5f3276-b4ba-414e-9d30-de9a04b76ab8	fact3	value3	3ded2c33-fe96-4c24-a257-d672eb577609	std::testing::NullResource[localhost,name=test3]	fact	2026-10-16 11:37:17.295477+02	{}	t
03ee434b-055b-49e9-8750-12e73692d7fa	parameter1	value1	3ded2c33-fe96-4c24-a257-d672eb577609		fact	2026-10-16 11:37:17.297708+02	{}	f
6b368dac-9cfb-4cd5-bb18-b477b32a16dd	parameter2	value2	3ded2c33-fe96-4c24-a257-d672eb577609		fact	2026-10-16 11:37:17.299889+02	{}	f
48ada515-f91e-426a-99f1-9221cd6f0c1f	parameter3	value3	3ded2c33-fe96-4c24-a257-d672eb577609		fact	2026-10-16 11:37:17.302036+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
dac8f722-9456-42aa-8a8c-4c1f9b530c26	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
b5b376f9-5d3e-49db-8775-5e0fb9167acf	2026-10-16 11:36:43.430724+02	2026-10-16 11:36:43.439576+02		Init		Using extra environment variables during compile \n	0	64027952-7eef-4a4f-b1fb-4682268d39a5
ab17010e-75e9-40a7-a736-af24f4b86825	2026-10-16 11:36:43.440499+02	2026-10-16 11:36:43.465505+02		Venv check		Creating new venv at /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env-py3.14\n	0	64027952-7eef-4a4f-b1fb-4682268d39a5
6f597785-0a87-492e-b2b8-84fbef205d61	2026-10-16 11:36:43.472367+02	2026-10-16 11:36:43.99786+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	64027952-7eef-4a4f-b1fb-4682268d39a5
9f305c66-a361-479c-a037-df1ec2866022	2026-10-16 11:37:13.635198+02	2026-10-16 11:37:13.643175+02		Init		Using extra environment variables during compile \n	0	c97b0f51-e9fc-4a2a-a080-f21e75b14d94
52864c07-5bfc-43e4-a7d5-534c1952659c	2026-10-16 11:37:13.644234+02	2026-10-16 11:37:13.646315+02		Venv check		Found existing venv\n	0	c97b0f51-e9fc-4a2a-a080-f21e75b14d94
04a7fe5e-6f89-42c3-bf52-368fc1e06ef2	2026-10-16 11:36:43.998847+02	2026-10-16 11:36:56.56465+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpgjrv2jg8:\n                                 Pip command: /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpgjrv2jg8 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, more-itertools, mitogen, jsonpath-ng, strawberry-graphql, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.10.1 mitogen-0.3.54 more-itertools-11.2.1 strawberry-graphql-0.335.0 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	64027952-7eef-4a4f-b1fb-4682268d39a5
ddc93774-4c23-49b9-8dd8-f3773879dcfe	2026-10-16 11:36:57.752801+02	2026-10-16 11:36:57.758141+02		Init		Using extra environment variables during compile \n	0	db6aea8a-6dcd-49de-89b4-e3aaa84b84a6
3edb739c-d475-47e6-83ab-63a3d7c17dbe	2026-10-16 11:36:57.758455+02	2026-10-16 11:36:57.770232+02		Venv check		Creating new venv at /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env-py3.14\n	0	db6aea8a-6dcd-49de-89b4-e3aaa84b84a6
d77848a7-e6d3-4c13-895e-2adbb567bdda	2026-10-16 11:36:57.772142+02	2026-10-16 11:36:58.116098+02	/tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	db6aea8a-6dcd-49de-89b4-e3aaa84b84a6
43b5254a-5847-406d-9a0e-ce132e87912a	2026-10-16 11:36:56.565533+02	2026-10-16 11:36:57.494502+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp293vauzv --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.028 seconds\ncompiler       DEBUG   The entire export command took 0.067 seconds\n	0	64027952-7eef-4a4f-b1fb-4682268d39a5
4c893f2d-78f4-45a3-a066-ce0fc4ca9499	2026-10-16 11:36:58.116901+02	2026-10-16 11:37:12.435261+02	/tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmppg34i9z6:\n                                 Pip command: /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmppg34i9z6 inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.1.0)\ninmanta.pip              DEBUG   Collecting more-itertools<12,>=8 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached more_itertools-11.2.1-py3-none-any.whl (74 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Collecting texttable~=1.0 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached texttable-1.7.1-py2.py3-none-any.whl (10 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.9.1)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.10.1-py3-none-any.whl (75 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.333.0)\ninmanta.pip              DEBUG   Collecting strawberry-graphql>=0.288.0 (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0)\ninmanta.pip              DEBUG   Using cached strawberry_graphql-0.335.0-py3-none-any.whl (358 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: texttable, more-itertools, mitogen, jsonpath-ng, strawberry-graphql, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: texttable\ninmanta.pip              DEBUG   Found existing installation: texttable 1.7.0\ninmanta.pip              DEBUG   Not uninstalling texttable at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'texttable'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: more-itertools\ninmanta.pip              DEBUG   Found existing installation: more-itertools 11.1.0\ninmanta.pip              DEBUG   Not uninstalling more-itertools at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'more-itertools'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.9.1\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: strawberry-graphql\ninmanta.pip              DEBUG   Found existing installation: strawberry-graphql 0.333.0\ninmanta.pip              DEBUG   Not uninstalling strawberry-graphql at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'strawberry-graphql'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.10.1 mitogen-0.3.54 more-itertools-11.2.1 strawberry-graphql-0.335.0 texttable-1.7.1\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	db6aea8a-6dcd-49de-89b4-e3aaa84b84a6
f4eace6f-aee8-4756-9e88-a446fa39f94a	2026-10-16 11:37:14.749677+02	2026-10-16 11:37:14.759286+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	f58a35e7-c51d-4035-b751-3d6dd7108bc4
bac7d7e3-9377-431b-bbd8-0d9ea107fc80	2026-10-16 11:37:14.760647+02	2026-10-16 11:37:14.763114+02		Venv check		Found existing venv\n	0	f58a35e7-c51d-4035-b751-3d6dd7108bc4
f4480bf8-9a05-484e-9e6c-f5a6cc633a3f	2026-10-16 11:37:12.435962+02	2026-10-16 11:37:13.371259+02	/tmp/tmpejcsy7uo/server/c2c8c1c1-ab22-48d5-844a-ede09b0ebd58/compiler/.env/bin/python -m inmanta.app -vvv export -X -e c2c8c1c1-ab22-48d5-844a-ede09b0ebd58 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpu7w0lhq0 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.052 seconds\n	0	db6aea8a-6dcd-49de-89b4-e3aaa84b84a6
49e33308-a83c-429c-81ba-76b1bc65e63f	2026-10-16 11:37:16.062883+02	2026-10-16 11:37:17.137774+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp70tm_1r8 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.008 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.019 seconds\ncompiler       DEBUG   The entire export command took 0.064 seconds\n	0	33d06477-9ced-4495-87dc-cfe111e4df00
3e3b43ad-04df-4286-aa0f-2c42bce4d718	2026-10-16 11:37:13.647226+02	2026-10-16 11:37:14.64301+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpoqahc5ht --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.010 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	c97b0f51-e9fc-4a2a-a080-f21e75b14d94
d3e22bf8-4fe1-4cb0-8692-7a5e4bea1fe8	2026-10-16 11:37:16.052206+02	2026-10-16 11:37:16.059007+02		Init		Using extra environment variables during compile \n	0	33d06477-9ced-4495-87dc-cfe111e4df00
b506b01e-6af9-4f8c-92a9-30e5e3cb4fd8	2026-10-16 11:37:16.060004+02	2026-10-16 11:37:16.062109+02		Venv check		Found existing venv\n	0	33d06477-9ced-4495-87dc-cfe111e4df00
29e97dfb-d01f-4885-9727-107646d5d485	2026-10-16 11:37:14.764054+02	2026-10-16 11:37:15.740946+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmph9tyol0d --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.008 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.012 seconds\ncompiler       DEBUG   The entire export command took 0.053 seconds\n	0	f58a35e7-c51d-4035-b751-3d6dd7108bc4
866c021e-7d9d-437a-bf8d-9a29f8266d97	2026-10-16 11:37:17.308461+02	2026-10-16 11:37:17.311255+02		Init		Using extra environment variables during compile \n	0	27592b0c-4cfd-4555-990e-bc2817e26141
f5683227-79f1-440d-b721-07bd75fb8bed	2026-10-16 11:37:17.311513+02	2026-10-16 11:37:17.3122+02		Venv check		Found existing venv\n	0	27592b0c-4cfd-4555-990e-bc2817e26141
356e5086-c9d0-4204-8321-426abe12c834	2026-10-16 11:37:18.437831+02	2026-10-16 11:37:18.439894+02		Init		Using extra environment variables during compile \n	0	aeac872f-c2fe-43cd-b170-ff0bcd36192c
6e7352ac-413a-4241-b29b-5a39ddff4a6d	2026-10-16 11:37:18.440107+02	2026-10-16 11:37:18.440492+02		Venv check		Found existing venv\n	0	aeac872f-c2fe-43cd-b170-ff0bcd36192c
dc75c11d-01f7-44b2-a35c-5bd8146e9645	2026-10-16 11:37:18.441729+02	2026-10-16 11:37:18.739602+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 20.1.0.dev0\nNot uninstalling inmanta-core at /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages, outside environment /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	aeac872f-c2fe-43cd-b170-ff0bcd36192c
e2effefd-f9a1-45ec-a53a-bbf3a9357454	2026-10-16 11:37:17.312393+02	2026-10-16 11:37:18.290814+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpuipz_hag --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.051 seconds\n	0	27592b0c-4cfd-4555-990e-bc2817e26141
dd1b969a-1631-4728-a895-5e7fd8dd8e1a	2026-10-16 11:37:18.740273+02	2026-10-16 11:37:36.890079+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp7j_mi5wo:\n                                 Pip command: /tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp7j_mi5wo inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==20.1.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==20.1.0.dev0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (20.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (26.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.1.4)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (3.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (1.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from inmanta-core==20.1.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from build~=1.0->inmanta-core==20.1.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==20.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==20.1.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from jinja2~=3.0->inmanta-core==20.1.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==20.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==20.1.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.288.0 in ./.env/lib/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.335.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==20.1.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==20.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (2026.7.22)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from strawberry-graphql>=0.288.0->strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==20.1.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2026.5)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==20.1.0.dev0) (7.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core314/lib/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==20.1.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	aeac872f-c2fe-43cd-b170-ff0bcd36192c
3d35a6bd-6bf8-47eb-98ac-d9f2d9eca321	2026-10-16 11:37:36.89088+02	2026-10-16 11:37:37.803655+02	/tmp/tmpejcsy7uo/server/3ded2c33-fe96-4c24-a257-d672eb577609/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 3ded2c33-fe96-4c24-a257-d672eb577609 --server_address localhost --server_port 50881 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpp18qnqqk --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:50881/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:50881/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.010 seconds\ncompiler       DEBUG   The entire export command took 0.050 seconds\n	0	aeac872f-c2fe-43cd-b170-ff0bcd36192c
0f810fdd-fd19-495d-91ac-c89437c20ce0	2026-10-16 11:37:38.86488+02	2026-10-16 11:37:38.874229+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpejcsy7uo/server/cf296431-1efb-4808-b601-c9ecc19cadca/compiler and no repository set.\n	1	a8386260-4d4a-44d0-a1d4-87ad9760b5a9
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	968c5ca7-e57a-4d33-800e-aa8f67b288c1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	0fa1a151-ee4b-47ef-a64a-8f6207a3503e
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0fa1a151-ee4b-47ef-a64a-8f6207a3503e
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	23069162-9308-4ba7-9758-83853a75c457
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	cb3a089c-0745-4c3b-8146-d1b7428d8b69
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	cb3a089c-0745-4c3b-8146-d1b7428d8b69
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	e96bb6b4-0753-4a5c-a407-2f1b467ee83e
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	6eeef6bb-ac44-4f9f-abbd-2c87d3f2dad6
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	decb298c-80dd-410f-8f42-b35f019befa1
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	7d23713d-54e0-4ff1-b83d-7caec4fe15f9
3ded2c33-fe96-4c24-a257-d672eb577609	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	9afa9775-4738-4a99-a435-19f1e1fc04a8
3ded2c33-fe96-4c24-a257-d672eb577609	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	640021ae-ca0c-48f2-83e1-9aa2f0975c16
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0430a52d-609f-4c62-a28e-20bf4e3c4be0
3ded2c33-fe96-4c24-a257-d672eb577609	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	7d7ff303-4313-4428-9ed7-aeda4c5558e7
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	a4ac8e8a-3372-450c-8c75-029fda129561
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	a4ac8e8a-3372-450c-8c75-029fda129561
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
4e9c52d1-31c1-43a5-a358-02ce5167f9c2	065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-16 11:37:38.611751+02
cc14f8b5-bdb8-4616-ba1a-eb2ed9fe10b9	065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-16 11:37:38.619806+02
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key1]	2026-10-16 11:37:38.433163+02	2026-10-16 11:37:38.380957+02	2026-10-16 11:37:38.433163+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.363319+02	t	\N	\N
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test]	2026-10-16 11:36:57.609999+02	\N	2026-10-16 11:36:57.609999+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:36:57.59776+02	f	\N	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key11]	2026-10-16 11:37:38.611751+02	\N	2026-10-16 11:37:38.611751+02	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.562277+02	f	4e9c52d1-31c1-43a5-a358-02ce5167f9c2	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Fail[agent1,key=key2]	2026-10-16 11:37:38.447983+02	\N	2026-10-16 11:37:38.447983+02	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:38.363319+02	f	\N	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	std::AgentConfig[internal,agentname=localhost]	2026-10-16 11:37:13.492188+02	\N	2026-10-16 11:37:13.492188+02	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:13.485431+02	f	\N	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key3]	2026-10-16 11:37:38.45823+02	\N	2026-10-16 11:37:38.45823+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-16 11:37:38.363319+02	f	\N	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	fs::File[localhost,path=/tmp/test]	2026-10-16 11:37:13.497945+02	\N	2026-10-16 11:37:13.497945+02	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:13.485431+02	f	\N	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key9]	2026-10-16 11:37:38.616001+02	2026-10-16 11:37:38.613056+02	2026-10-16 11:37:38.616001+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.562277+02	t	\N	\N
3ded2c33-fe96-4c24-a257-d672eb577609	fs::File[localhost,path=/tmp/test_orphan]	2026-10-16 11:37:15.915041+02	\N	2026-10-16 11:37:15.915041+02	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:15.906311+02	f	\N	3
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key10]	2026-10-16 11:37:38.619806+02	\N	2026-10-16 11:37:38.619806+02	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.562277+02	f	cc14f8b5-bdb8-4616-ba1a-eb2ed9fe10b9	\N
3ded2c33-fe96-4c24-a257-d672eb577609	test::Resource[agent2,key=key2]	2026-10-16 11:37:38.013362+02	\N	2026-10-16 11:37:38.013362+02	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:38.004389+02	f	\N	\N
3ded2c33-fe96-4c24-a257-d672eb577609	test::Resource[agent3,key=key3]	2026-10-16 11:37:38.011355+02	\N	2026-10-16 11:37:38.011355+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-16 11:37:38.004389+02	f	\N	7
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-16 11:37:38.363319+02	\N	\N	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-16 11:37:38.363319+02	\N	\N	\N
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key6]	2026-10-16 11:37:38.462336+02	2026-10-16 11:37:38.459077+02	2026-10-16 11:37:38.462336+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.363319+02	t	\N	1
065285aa-140b-49d3-bae9-380fef7e0573	test::Resource[agent1,key=key7]	2026-10-16 11:37:38.607755+02	2026-10-16 11:37:38.602729+02	2026-10-16 11:37:38.607755+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-16 11:37:38.562277+02	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	968c5ca7-e57a-4d33-800e-aa8f67b288c1	\N
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	0fa1a151-ee4b-47ef-a64a-8f6207a3503e	\N
3ded2c33-fe96-4c24-a257-d672eb577609	23069162-9308-4ba7-9758-83853a75c457	\N
3ded2c33-fe96-4c24-a257-d672eb577609	cb3a089c-0745-4c3b-8146-d1b7428d8b69	\N
3ded2c33-fe96-4c24-a257-d672eb577609	e96bb6b4-0753-4a5c-a407-2f1b467ee83e	\N
3ded2c33-fe96-4c24-a257-d672eb577609	6eeef6bb-ac44-4f9f-abbd-2c87d3f2dad6	\N
3ded2c33-fe96-4c24-a257-d672eb577609	decb298c-80dd-410f-8f42-b35f019befa1	\N
3ded2c33-fe96-4c24-a257-d672eb577609	7d23713d-54e0-4ff1-b83d-7caec4fe15f9	\N
3ded2c33-fe96-4c24-a257-d672eb577609	9afa9775-4738-4a99-a435-19f1e1fc04a8	set-b
3ded2c33-fe96-4c24-a257-d672eb577609	640021ae-ca0c-48f2-83e1-9aa2f0975c16	set-a
3ded2c33-fe96-4c24-a257-d672eb577609	0430a52d-609f-4c62-a28e-20bf4e3c4be0	\N
3ded2c33-fe96-4c24-a257-d672eb577609	7d7ff303-4313-4428-9ed7-aeda4c5558e7	set-a
065285aa-140b-49d3-bae9-380fef7e0573	72c881fc-b9cb-4197-bc38-6aba6f40e93b	\N
065285aa-140b-49d3-bae9-380fef7e0573	1e36ebf0-0252-4ea5-afcd-075069b6e3bc	\N
065285aa-140b-49d3-bae9-380fef7e0573	a4ac8e8a-3372-450c-8c75-029fda129561	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	1	968c5ca7-e57a-4d33-800e-aa8f67b288c1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	0fa1a151-ee4b-47ef-a64a-8f6207a3503e
3ded2c33-fe96-4c24-a257-d672eb577609	2	23069162-9308-4ba7-9758-83853a75c457
3ded2c33-fe96-4c24-a257-d672eb577609	3	cb3a089c-0745-4c3b-8146-d1b7428d8b69
3ded2c33-fe96-4c24-a257-d672eb577609	4	e96bb6b4-0753-4a5c-a407-2f1b467ee83e
3ded2c33-fe96-4c24-a257-d672eb577609	5	6eeef6bb-ac44-4f9f-abbd-2c87d3f2dad6
3ded2c33-fe96-4c24-a257-d672eb577609	6	decb298c-80dd-410f-8f42-b35f019befa1
3ded2c33-fe96-4c24-a257-d672eb577609	7	7d23713d-54e0-4ff1-b83d-7caec4fe15f9
3ded2c33-fe96-4c24-a257-d672eb577609	7	9afa9775-4738-4a99-a435-19f1e1fc04a8
3ded2c33-fe96-4c24-a257-d672eb577609	7	640021ae-ca0c-48f2-83e1-9aa2f0975c16
3ded2c33-fe96-4c24-a257-d672eb577609	8	0430a52d-609f-4c62-a28e-20bf4e3c4be0
3ded2c33-fe96-4c24-a257-d672eb577609	8	7d7ff303-4313-4428-9ed7-aeda4c5558e7
065285aa-140b-49d3-bae9-380fef7e0573	1	72c881fc-b9cb-4197-bc38-6aba6f40e93b
065285aa-140b-49d3-bae9-380fef7e0573	2	1e36ebf0-0252-4ea5-afcd-075069b6e3bc
065285aa-140b-49d3-bae9-380fef7e0573	3	a4ac8e8a-3372-450c-8c75-029fda129561
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
c7449602-de62-4b0b-b16a-73eaccf8d2df	store	2026-10-16 11:36:57.471242+02	2026-10-16 11:36:57.483107+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:36:57.483119+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	1	{"fs::File[localhost,path=/tmp/test],v=1"}
4547aba4-8e89-4be0-a40d-8c9e8b860be0	deploy	2026-10-16 11:36:57.603644+02	2026-10-16 11:36:57.609999+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:36:57.609183+02:00\\"}"}	unavailable	\N	nochange	3ded2c33-fe96-4c24-a257-d672eb577609	1	{"fs::File[localhost,path=/tmp/test],v=1"}
9e3bc07a-9db4-457c-9ca6-b076fd4e0f0b	store	2026-10-16 11:37:13.356721+02	2026-10-16 11:37:13.362961+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:37:13.362971+02:00\\"}"}	\N	\N	\N	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
75805074-79bb-4bc7-b23b-5c3218b36db8	deploy	2026-10-16 11:37:13.490557+02	2026-10-16 11:37:13.492188+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:13.491666+02:00\\"}"}	unavailable	\N	nochange	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
6ac03559-b6bc-4d17-8e69-dfcb5cc0db25	deploy	2026-10-16 11:37:13.49674+02	2026-10-16 11:37:13.497945+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:13.497468+02:00\\"}"}	unavailable	\N	nochange	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1	{"fs::File[localhost,path=/tmp/test],v=1"}
ac6745b8-b1d7-4514-9043-15ffc94e06e3	store	2026-10-16 11:37:14.634093+02	2026-10-16 11:37:14.636131+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-16T11:37:14.636141+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	2	{"fs::File[localhost,path=/tmp/test],v=2"}
20a19edf-b691-4b56-89d2-e065efaaddf2	store	2026-10-16 11:37:15.731126+02	2026-10-16 11:37:15.733222+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-16T11:37:15.733231+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3","fs::File[localhost,path=/tmp/test],v=3"}
13741f6d-edad-402a-a021-2237a78dd36c	deploy	2026-10-16 11:37:15.909706+02	2026-10-16 11:37:15.915041+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-16T11:37:15.914298+02:00\\"}"}	unavailable	\N	nochange	3ded2c33-fe96-4c24-a257-d672eb577609	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
f160dc65-9a2c-4717-a825-8b2a74f7a15c	store	2026-10-16 11:37:17.121772+02	2026-10-16 11:37:17.127537+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-16T11:37:17.127548+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	4	{"fs::File[localhost,path=/tmp/test],v=4"}
bf05395a-a3a6-433c-84cf-bbb90cf938eb	store	2026-10-16 11:37:18.27404+02	2026-10-16 11:37:18.276072+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-16T11:37:18.276082+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	5	{"fs::File[localhost,path=/tmp/test],v=5"}
4e7c87c6-b9a4-42fa-9991-348cc5befe52	store	2026-10-16 11:37:37.791064+02	2026-10-16 11:37:37.793166+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-16T11:37:37.793175+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	6	{"fs::File[localhost,path=/tmp/test],v=6"}
1726e74f-1e9a-49a2-b9c0-07faee07ee8b	store	2026-10-16 11:37:37.971717+02	2026-10-16 11:37:37.979666+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-16T11:37:37.979680+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	7	{"test::Resource[agent3,key=key3],v=7","test::Resource[agent2,key=key2],v=7","fs::File[localhost,path=/tmp/test],v=7"}
881a6c09-589f-482e-9686-2698a09db04c	deploy	2026-10-16 11:37:38.009709+02	2026-10-16 11:37:38.011355+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.010806+02:00\\"}"}	unavailable	\N	nochange	3ded2c33-fe96-4c24-a257-d672eb577609	7	{"test::Resource[agent3,key=key3],v=7"}
74a12259-16ef-4758-b349-9745ee89fcc4	deploy	2026-10-16 11:37:38.011421+02	2026-10-16 11:37:38.013362+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.012857+02:00\\"}"}	unavailable	\N	nochange	3ded2c33-fe96-4c24-a257-d672eb577609	7	{"test::Resource[agent2,key=key2],v=7"}
3dc57bf0-dbfc-46a9-a1f3-10619876513e	store	2026-10-16 11:37:38.148483+02	2026-10-16 11:37:38.166205+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-16T11:37:38.166216+02:00\\"}"}	\N	\N	\N	3ded2c33-fe96-4c24-a257-d672eb577609	8	{"test::Resource[agent2,key=key2],v=8","fs::File[localhost,path=/tmp/test],v=8"}
db4b5a4d-569c-4f07-8fb5-cb933008a666	store	2026-10-16 11:37:38.333608+02	2026-10-16 11:37:38.340489+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-16T11:37:38.340523+02:00\\"}"}	\N	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key4],v=1","test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key6],v=1"}
48db2c43-9cf5-441d-9c6b-1fe8fcb937e3	deploy	2026-10-16 11:37:38.3811+02	2026-10-16 11:37:38.433163+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: e015e803-0ed5-4629-9fe3-0b12e5d32604).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"e015e803-0ed5-4629-9fe3-0b12e5d32604\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.412444+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: e015e803-0ed5-4629-9fe3-0b12e5d32604) - duration: 0.0203 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.020349502563476562, \\"deploy_id\\": \\"e015e803-0ed5-4629-9fe3-0b12e5d32604\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.433007+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key1],v=1"}
a58ab17b-59a8-4f34-a4d4-037d28efee0e	deploy	2026-10-16 11:37:38.439722+02	2026-10-16 11:37:38.447983+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 1ac74c51-e5a3-4f10-853c-5b3dbd108489).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"1ac74c51-e5a3-4f10-853c-5b3dbd108489\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.444488+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.446217+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 1ac74c51-e5a3-4f10-853c-5b3dbd108489) - duration: 0.0032 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.0031812191009521484, \\"deploy_id\\": \\"1ac74c51-e5a3-4f10-853c-5b3dbd108489\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.447863+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Fail[agent1,key=key2],v=1"}
11ea1a6d-cc38-442a-afd3-fd6a98c2db45	deploy	2026-10-16 11:37:38.4538+02	2026-10-16 11:37:38.45823+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 578551ca-9923-4f8a-ba29-19b788c59bca).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"578551ca-9923-4f8a-ba29-19b788c59bca\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.457821+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.458100+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 578551ca-9923-4f8a-ba29-19b788c59bca) - duration: 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0003101825714111328, \\"deploy_id\\": \\"578551ca-9923-4f8a-ba29-19b788c59bca\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.458206+02:00\\"}"}	skipped	\N	nochange	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key3],v=1"}
a322e1ed-b33d-4ae7-8d3f-f0ea3946b063	deploy	2026-10-16 11:37:38.459103+02	2026-10-16 11:37:38.462336+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 81ac69ad-544b-4d24-8c6c-6bb618fab952).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"81ac69ad-544b-4d24-8c6c-6bb618fab952\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.459733+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 81ac69ad-544b-4d24-8c6c-6bb618fab952) - duration: 0.0025 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.002535581588745117, \\"deploy_id\\": \\"81ac69ad-544b-4d24-8c6c-6bb618fab952\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.462308+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key6],v=1"}
5210a278-42c3-4f5d-8116-985d8c8fd1fb	dryrun	2026-10-16 11:37:38.521363+02	2026-10-16 11:37:38.522374+02	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.521536+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006470680236816406, \\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.522322+02:00\\"}"}	dry	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Fail[agent1,key=key2],v=1"}
05740d85-9866-42fa-a1f6-6d0fe96b37a3	store	2026-10-16 11:37:38.551301+02	2026-10-16 11:37:38.559804+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-16T11:37:38.559810+02:00\\"}"}	\N	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	2	{"test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key4],v=2","test::Resource[agent1,key=key7],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key11],v=2"}
5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	store	2026-10-16 11:37:38.716915+02	2026-10-16 11:37:38.723956+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-16T11:37:38.723982+02:00\\"}"}	\N	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	3	{"test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key4],v=3","test::Resource[agent1,key=key5],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key1],v=3"}
a1c2d285-811e-4d55-87ba-103d9625c8f2	dryrun	2026-10-16 11:37:38.540224+02	2026-10-16 11:37:38.541145+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.540376+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0005817413330078125, \\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.541100+02:00\\"}"}	dry	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key1],v=1"}
a1e30143-aee9-4e3c-bbb5-cd397a9536c1	dryrun	2026-10-16 11:37:38.554296+02	2026-10-16 11:37:38.55456+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.554339+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d - duration 0.0002 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00016999244689941406, \\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.554546+02:00\\"}"}	dry	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key3],v=1"}
9340cb3a-0301-4dbb-ba2a-018b0f7c252d	dryrun	2026-10-16 11:37:38.55661+02	2026-10-16 11:37:38.556799+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.556653+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d - duration 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00009894371032714844, \\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.556788+02:00\\"}"}	dry	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key5],v=1"}
cea11bb8-6d0b-4785-8654-55c9036c8c70	dryrun	2026-10-16 11:37:38.558745+02	2026-10-16 11:37:38.558978+02	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.558785+02:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 526203f5-d87e-4f85-99ea-fd3ddbb8946d - duration 0.0001 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00014328956604003906, \\"dry_run_id\\": \\"526203f5-d87e-4f85-99ea-fd3ddbb8946d\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.558965+02:00\\"}"}	dry	\N	\N	065285aa-140b-49d3-bae9-380fef7e0573	1	{"test::Resource[agent1,key=key6],v=1"}
8cd364ec-e2b5-4fc5-9cf2-f76d77e382f3	deploy	2026-10-16 11:37:38.602776+02	2026-10-16 11:37:38.607755+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: da8bbe99-8adf-4095-b488-793cccb09cc7).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"da8bbe99-8adf-4095-b488-793cccb09cc7\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.604257+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: da8bbe99-8adf-4095-b488-793cccb09cc7) - duration: 0.0034 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.003415346145629883, \\"deploy_id\\": \\"da8bbe99-8adf-4095-b488-793cccb09cc7\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.607722+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	065285aa-140b-49d3-bae9-380fef7e0573	2	{"test::Resource[agent1,key=key7],v=2"}
85dba455-8bf1-4929-9dad-7c7ef221f0b7	deploy	2026-10-16 11:37:38.608727+02	2026-10-16 11:37:38.611751+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ce2a347f-013f-4f73-a660-22b6ff96d05a).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"ce2a347f-013f-4f73-a660-22b6ff96d05a\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.609325+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.609461+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: ce2a347f-013f-4f73-a660-22b6ff96d05a) - duration: 0.0024 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.0023539066314697266, \\"deploy_id\\": \\"ce2a347f-013f-4f73-a660-22b6ff96d05a\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.611720+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	065285aa-140b-49d3-bae9-380fef7e0573	2	{"test::Resource[agent1,key=key11],v=2"}
86367e21-d312-4e6d-84ff-531b139368e6	deploy	2026-10-16 11:37:38.613086+02	2026-10-16 11:37:38.616001+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: add8f179-9812-4228-ab8f-b0e6b74f5506).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"add8f179-9812-4228-ab8f-b0e6b74f5506\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.613688+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: add8f179-9812-4228-ab8f-b0e6b74f5506) - duration: 0.0022 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.0022454261779785156, \\"deploy_id\\": \\"add8f179-9812-4228-ab8f-b0e6b74f5506\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.615973+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	065285aa-140b-49d3-bae9-380fef7e0573	2	{"test::Resource[agent1,key=key9],v=2"}
bc699b0c-42d8-4560-8083-07ce0b45db0f	deploy	2026-10-16 11:37:38.616876+02	2026-10-16 11:37:38.619806+02	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: ab2850bb-df91-45d3-a78e-a1712c32a0ab).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"ab2850bb-df91-45d3-a78e-a1712c32a0ab\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.617449+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.617648+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: ab2850bb-df91-45d3-a78e-a1712c32a0ab) - duration: 0.0023 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.002290487289428711, \\"deploy_id\\": \\"ab2850bb-df91-45d3-a78e-a1712c32a0ab\\"}, \\"timestamp\\": \\"2026-10-16T11:37:38.619779+02:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	065285aa-140b-49d3-bae9-380fef7e0573	2	{"test::Resource[agent1,key=key10],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
3ded2c33-fe96-4c24-a257-d672eb577609	c7449602-de62-4b0b-b16a-73eaccf8d2df	fs::File[localhost,path=/tmp/test]	1
3ded2c33-fe96-4c24-a257-d672eb577609	4547aba4-8e89-4be0-a40d-8c9e8b860be0	fs::File[localhost,path=/tmp/test]	1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	9e3bc07a-9db4-457c-9ca6-b076fd4e0f0b	fs::File[localhost,path=/tmp/test]	1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	9e3bc07a-9db4-457c-9ca6-b076fd4e0f0b	std::AgentConfig[internal,agentname=localhost]	1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	75805074-79bb-4bc7-b23b-5c3218b36db8	std::AgentConfig[internal,agentname=localhost]	1
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	6ac03559-b6bc-4d17-8e69-dfcb5cc0db25	fs::File[localhost,path=/tmp/test]	1
3ded2c33-fe96-4c24-a257-d672eb577609	ac6745b8-b1d7-4514-9043-15ffc94e06e3	fs::File[localhost,path=/tmp/test]	2
3ded2c33-fe96-4c24-a257-d672eb577609	20a19edf-b691-4b56-89d2-e065efaaddf2	fs::File[localhost,path=/tmp/test_orphan]	3
3ded2c33-fe96-4c24-a257-d672eb577609	20a19edf-b691-4b56-89d2-e065efaaddf2	fs::File[localhost,path=/tmp/test]	3
3ded2c33-fe96-4c24-a257-d672eb577609	13741f6d-edad-402a-a021-2237a78dd36c	fs::File[localhost,path=/tmp/test_orphan]	3
3ded2c33-fe96-4c24-a257-d672eb577609	f160dc65-9a2c-4717-a825-8b2a74f7a15c	fs::File[localhost,path=/tmp/test]	4
3ded2c33-fe96-4c24-a257-d672eb577609	bf05395a-a3a6-433c-84cf-bbb90cf938eb	fs::File[localhost,path=/tmp/test]	5
3ded2c33-fe96-4c24-a257-d672eb577609	4e7c87c6-b9a4-42fa-9991-348cc5befe52	fs::File[localhost,path=/tmp/test]	6
3ded2c33-fe96-4c24-a257-d672eb577609	1726e74f-1e9a-49a2-b9c0-07faee07ee8b	test::Resource[agent3,key=key3]	7
3ded2c33-fe96-4c24-a257-d672eb577609	1726e74f-1e9a-49a2-b9c0-07faee07ee8b	test::Resource[agent2,key=key2]	7
3ded2c33-fe96-4c24-a257-d672eb577609	1726e74f-1e9a-49a2-b9c0-07faee07ee8b	fs::File[localhost,path=/tmp/test]	7
3ded2c33-fe96-4c24-a257-d672eb577609	881a6c09-589f-482e-9686-2698a09db04c	test::Resource[agent3,key=key3]	7
3ded2c33-fe96-4c24-a257-d672eb577609	74a12259-16ef-4758-b349-9745ee89fcc4	test::Resource[agent2,key=key2]	7
3ded2c33-fe96-4c24-a257-d672eb577609	3dc57bf0-dbfc-46a9-a1f3-10619876513e	test::Resource[agent2,key=key2]	8
3ded2c33-fe96-4c24-a257-d672eb577609	3dc57bf0-dbfc-46a9-a1f3-10619876513e	fs::File[localhost,path=/tmp/test]	8
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Resource[agent1,key=key3]	1
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Resource[agent1,key=key1]	1
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Resource[agent1,key=key4]	1
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Fail[agent1,key=key2]	1
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Resource[agent1,key=key5]	1
065285aa-140b-49d3-bae9-380fef7e0573	db4b5a4d-569c-4f07-8fb5-cb933008a666	test::Resource[agent1,key=key6]	1
065285aa-140b-49d3-bae9-380fef7e0573	48db2c43-9cf5-441d-9c6b-1fe8fcb937e3	test::Resource[agent1,key=key1]	1
065285aa-140b-49d3-bae9-380fef7e0573	a58ab17b-59a8-4f34-a4d4-037d28efee0e	test::Fail[agent1,key=key2]	1
065285aa-140b-49d3-bae9-380fef7e0573	11ea1a6d-cc38-442a-afd3-fd6a98c2db45	test::Resource[agent1,key=key3]	1
065285aa-140b-49d3-bae9-380fef7e0573	a322e1ed-b33d-4ae7-8d3f-f0ea3946b063	test::Resource[agent1,key=key6]	1
065285aa-140b-49d3-bae9-380fef7e0573	5210a278-42c3-4f5d-8116-985d8c8fd1fb	test::Fail[agent1,key=key2]	1
065285aa-140b-49d3-bae9-380fef7e0573	a1c2d285-811e-4d55-87ba-103d9625c8f2	test::Resource[agent1,key=key1]	1
065285aa-140b-49d3-bae9-380fef7e0573	a1e30143-aee9-4e3c-bbb5-cd397a9536c1	test::Resource[agent1,key=key3]	1
065285aa-140b-49d3-bae9-380fef7e0573	9340cb3a-0301-4dbb-ba2a-018b0f7c252d	test::Resource[agent1,key=key5]	1
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key9]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key1]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key10]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key5]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key3]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key4]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key7]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Fail[agent1,key=key2]	2
065285aa-140b-49d3-bae9-380fef7e0573	05740d85-9866-42fa-a1f6-6d0fe96b37a3	test::Resource[agent1,key=key11]	2
065285aa-140b-49d3-bae9-380fef7e0573	cea11bb8-6d0b-4785-8654-55c9036c8c70	test::Resource[agent1,key=key6]	1
065285aa-140b-49d3-bae9-380fef7e0573	8cd364ec-e2b5-4fc5-9cf2-f76d77e382f3	test::Resource[agent1,key=key7]	2
065285aa-140b-49d3-bae9-380fef7e0573	85dba455-8bf1-4929-9dad-7c7ef221f0b7	test::Resource[agent1,key=key11]	2
065285aa-140b-49d3-bae9-380fef7e0573	86367e21-d312-4e6d-84ff-531b139368e6	test::Resource[agent1,key=key9]	2
065285aa-140b-49d3-bae9-380fef7e0573	bc699b0c-42d8-4560-8083-07ce0b45db0f	test::Resource[agent1,key=key10]	2
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key3]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key7]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key4]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key5]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Fail[agent1,key=key2]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key8]	3
065285aa-140b-49d3-bae9-380fef7e0573	5c1b2a6e-a79f-46a8-a4c7-04d0c48a361f	test::Resource[agent1,key=key1]	3
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
c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	1
3ded2c33-fe96-4c24-a257-d672eb577609	8
065285aa-140b-49d3-bae9-380fef7e0573	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	3ded2c33-fe96-4c24-a257-d672eb577609	2026-10-16 11:36:43.126053+02	\N	7049799d-0fe2-498c-aa96-337dccfe898e
hugo-Latitude-5421	c2c8c1c1-ab22-48d5-844a-ede09b0ebd58	2026-10-16 11:36:43.233727+02	\N	482167aa-465d-45c5-adc1-1855b6f395a0
hugo-Latitude-5421	065285aa-140b-49d3-bae9-380fef7e0573	2026-10-16 11:37:38.19641+02	2026-10-16 11:37:38.702344+02	1f3c60a1-4d9e-44b3-8298-10e87021e11b
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610161}
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

