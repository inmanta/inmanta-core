--
-- PostgreSQL database dump
--

--\restrict CJMRxhNTu41sVfkXnO661KcGE3ypI4D1wBbcHg3tpp2CUUEw9G7cqh2N3mTDVZw

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
6c727c98-6b55-4b9d-827d-dc48c90136ca	$__scheduler	f	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	$__scheduler	f	\N
f28bfddb-0c73-4e04-a58e-85ab2cb17fa3	$__scheduler	f	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	localhost	f	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	internal	f	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	localhost	f	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	agent3	f	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	agent2	f	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	agent1	t	t
336135a6-cee1-4a5c-81f8-dbda19ed9801	$__scheduler	t	t
427218da-a7a5-4aed-a950-2b6c55ffbd14	$__scheduler	f	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, environment) FROM stdin;
1	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
1	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
1	internal	std	6d05d33c-20da-450d-8ba3-e651c83aeda3
1	localhost	fs	6d05d33c-20da-450d-8ba3-e651c83aeda3
2	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
2	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
3	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
3	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
4	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
4	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
5	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
5	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
6	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
6	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
7	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
7	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
8	localhost	fs	6c727c98-6b55-4b9d-827d-dc48c90136ca
8	localhost	std	6c727c98-6b55-4b9d-827d-dc48c90136ca
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links, reinstall_project_and_venv) FROM stdin;
b2435a90-62d2-4792-be8c-7ed76b2004a8	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:25.097789+00	2026-10-28 11:23:31.826576+00	2026-10-28 11:23:25.058785+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	da2890b4-c8bc-409f-a798-fda039583120	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
241de1e7-60f3-44b9-a62e-99294e0ee99b	6d05d33c-20da-450d-8ba3-e651c83aeda3	2026-10-28 11:23:32.03203+00	2026-10-28 11:23:36.398842+00	2026-10-28 11:23:32.014617+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	243fe52c-e403-41b3-8b55-9c7fc549fcba	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
859d28b7-c34d-4373-a750-fe408024683d	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:36.685354+00	2026-10-28 11:23:37.750667+00	2026-10-28 11:23:36.657795+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	ffab1dea-583a-4fde-9e7d-6a41f2b80d4a	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
685b8eb0-cf59-407c-94a7-9639122a6058	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:37.884567+00	2026-10-28 11:23:38.938476+00	2026-10-28 11:23:37.872998+00	{}	{"add_one_resource": "true"}	t	f	t	3	53cd4908-0537-48e8-a4fc-92cfd236a673	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}	f
0b0626a3-391c-4715-b548-ecf5f312dd23	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:39.265135+00	2026-10-28 11:23:40.282149+00	2026-10-28 11:23:39.246425+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	4b4edef1-3795-47cb-8f14-69962060f768	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
c0e588cc-d217-4a0b-b26f-f6564e9b0a16	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:40.465929+00	2026-10-28 11:23:41.478641+00	2026-10-28 11:23:40.452035+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	e258d48b-8d41-4530-9c16-75ffbd63c55f	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
63791996-051a-43de-a3c3-f538b5149696	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:41.580097+00	2026-10-28 11:23:45.576896+00	2026-10-28 11:23:41.560494+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	0e6c67dd-ee4f-45ef-afa0-f671801edfbc	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}	f
97b06af4-dddb-4d3e-ac52-382ec7415f0e	427218da-a7a5-4aed-a950-2b6c55ffbd14	2026-10-28 11:23:46.944805+00	2026-10-28 11:23:46.984227+00	2026-10-28 11:23:46.905958+00	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	cddd829a-4973-4e8b-ba71-fa070f3b95f0	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}	f
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
1	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:31.747786+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
1	6d05d33c-20da-450d-8ba3-e651c83aeda3	2026-10-28 11:23:36.327005+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	inmanta-module-std<8
2	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:37.667343+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:38.873669+00	t	{"export_metadata": {"type": "manual", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	2	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
4	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:40.224087+00	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:41.421611+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:45.522245+00	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "jp", "hostname": "NOSdrive", "inmanta:compile:state": "success"}}	1	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:45.669302+00	t	\N	3	6	t	\N	\N
8	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:45.85283+00	t	\N	2	7	t	\N	\N
1	336135a6-cee1-4a5c-81f8-dbda19ed9801	2026-10-28 11:23:46.0936+00	t	\N	6	\N	t	\N	\N
2	336135a6-cee1-4a5c-81f8-dbda19ed9801	2026-10-28 11:23:46.416052+00	t	\N	9	\N	t	\N	\N
3	336135a6-cee1-4a5c-81f8-dbda19ed9801	2026-10-28 11:23:46.725862+00	f	\N	7	\N	t	\N	\N
\.


--
-- Data for Name: configurationmodel_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel_modules (environment, cm_version, inmanta_module_name, inmanta_module_version) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	1	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	1	fs	1.2.0
6d05d33c-20da-450d-8ba3-e651c83aeda3	1	std	7.0.0
6d05d33c-20da-450d-8ba3-e651c83aeda3	1	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	2	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	2	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	3	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	3	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	4	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	4	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	5	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	5	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	6	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	6	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	7	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	7	std	8.7.5
6c727c98-6b55-4b9d-827d-dc48c90136ca	8	fs	1.2.0
6c727c98-6b55-4b9d-827d-dc48c90136ca	8	std	8.7.5
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	discovery::Discovered[myagent,name=discovered]	{}	2026-10-28 11:23:46.746175+00	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
6c727c98-6b55-4b9d-827d-dc48c90136ca	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2026-10-28 11:23:46.746208+00	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources, resource_filter, context) FROM stdin;
64f1c62d-0d21-4a76-9789-811473dc514b	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	2026-10-28 11:23:46.365869+00	6	0	{"0bd9c2d3-dd4f-5b54-97d3-8b2a2b5bbf39": {"id": "test::Resource[agent1,key=key1],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key1"}}, "2cfae911-b925-5f6b-9469-8267ce7d0d7e": {"id": "test::Resource[agent1,key=key6],v=1", "changes": {}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key6"}}, "568f19ce-35d7-5c05-a40e-4c4d52d8f3b6": {"id": "test::Resource[agent1,key=key5],v=1", "changes": {"value": {"current": null, "desired": "val5"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key5"}}, "7d52e8f4-1c54-52d2-ab2e-7d8fb79bc1de": {"id": "test::Fail[agent1,key=key2],v=1", "changes": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Fail", "attribute_value": "key2"}}, "84078789-38ae-5966-88eb-65e00a518a47": {"id": "test::Resource[agent1,key=key4],v=1", "changes": {}, "id_fields": {"attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key4"}, "diff_status": "undefined"}, "b8a42c4f-340e-549a-8a11-168b4d0744fb": {"id": "test::Resource[agent1,key=key3],v=1", "changes": {"value": {"current": null, "desired": "val3"}, "purged": {"current": true, "desired": false}}, "id_fields": {"version": 1, "attribute": "key", "agent_name": "agent1", "entity_type": "test::Resource", "attribute_value": "key3"}}}	\N	\N
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
f28bfddb-0c73-4e04-a58e-85ab2cb17fa3	dev-2	7f68b518-9085-4ffd-9011-ef5717021749			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
6c727c98-6b55-4b9d-827d-dc48c90136ca	dev-1	7f68b518-9085-4ffd-9011-ef5717021749			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
6d05d33c-20da-450d-8ba3-e651c83aeda3	dev-1-twin	7f68b518-9085-4ffd-9011-ef5717021749			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	1	f			f
427218da-a7a5-4aed-a950-2b6c55ffbd14	dev-4	7f68b518-9085-4ffd-9011-ef5717021749			{"settings": {"auto_deploy": {"value": true, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "600", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "86400", "protected": false, "protected_by": null}}}	0	f			f
336135a6-cee1-4a5c-81f8-dbda19ed9801	dev-3	7f68b518-9085-4ffd-9011-ef5717021749			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "autostart_on_start": {"value": true, "protected": false, "protected_by": null}, "protected_environment": {"value": false, "protected": false, "protected_by": null}, "notification_retention": {"value": 365, "protected": false, "protected_by": null}, "redeploy_failed_on_export": {"value": false, "protected": false, "protected_by": null}, "available_versions_to_keep": {"value": 100, "protected": false, "protected_by": null}, "environment_metrics_retention": {"value": 336, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "resource_action_logs_retention": {"value": 7, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
std	8.7.5	6c727c98-6b55-4b9d-827d-dc48c90136ca	{}	f
fs	1.2.0	6c727c98-6b55-4b9d-827d-dc48c90136ca	{}	f
std	7.0.0	6d05d33c-20da-450d-8ba3-e651c83aeda3	{}	f
fs	1.2.0	6d05d33c-20da-450d-8ba3-e651c83aeda3	{}	f
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
6fff0ce8-afda-4cf5-800a-87f3318cd2cf	427218da-a7a5-4aed-a950-2b6c55ffbd14	2026-10-28 11:23:47.000135+00	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/97b06af4-dddb-4d3e-ac52-382ec7415f0e	f	f	97b06af4-dddb-4d3e-ac52-382ec7415f0e
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
5814a41d-16dc-4946-9043-d5ba3133f65a	fact1	value1	6c727c98-6b55-4b9d-827d-dc48c90136ca	std::testing::NullResource[localhost,name=test1]	fact	2026-10-28 11:23:40.375019+00	{}	f
51c66cf4-7210-4d99-ad33-4f21c07d6b2c	fact2	value2	6c727c98-6b55-4b9d-827d-dc48c90136ca	std::testing::NullResource[localhost,name=test2]	fact	2026-10-28 11:23:40.391858+00	{}	t
5c012a8c-8fd0-422c-b8ce-5f060f798a9c	fact3	value3	6c727c98-6b55-4b9d-827d-dc48c90136ca	std::testing::NullResource[localhost,name=test3]	fact	2026-10-28 11:23:40.40514+00	{}	t
840b51d5-7c32-4542-9999-b7d55e839d4a	parameter1	value1	6c727c98-6b55-4b9d-827d-dc48c90136ca		fact	2026-10-28 11:23:40.417781+00	{}	f
b5c281ee-2f78-41e9-9e32-f4ccd944619e	parameter2	value2	6c727c98-6b55-4b9d-827d-dc48c90136ca		fact	2026-10-28 11:23:40.429996+00	{}	f
705eb2aa-765d-4836-9937-9a3a3d321284	parameter3	value3	6c727c98-6b55-4b9d-827d-dc48c90136ca		fact	2026-10-28 11:23:40.441148+00	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
7f68b518-9085-4ffd-9011-ef5717021749	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
123f4662-be34-48c8-9874-fd9f1a7a7224	2026-10-28 11:23:25.108167+00	2026-10-28 11:23:25.135188+00		Init		Using extra environment variables during compile \n	0	b2435a90-62d2-4792-be8c-7ed76b2004a8
dae7384e-59b2-4c30-bd31-3962389cc176	2026-10-28 11:23:25.14477+00	2026-10-28 11:23:25.167476+00		Venv check		Creating new venv at /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env-py3.14\n	0	b2435a90-62d2-4792-be8c-7ed76b2004a8
d7f06abf-653e-482d-8399-289d296ed2b3	2026-10-28 11:23:25.180132+00	2026-10-28 11:23:25.546539+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	b2435a90-62d2-4792-be8c-7ed76b2004a8
c7dadab4-f7b4-4a4a-8d74-a7c802c8b464	2026-10-28 11:23:25.554598+00	2026-10-28 11:23:30.770429+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmp3pylmruu:\n                                 Pip command: /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmp3pylmruu inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.13.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Downloading jsonpath_ng-1.14.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Downloading jsonpath_ng-1.14.0-py3-none-any.whl (84 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (529 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: tornado, mitogen, jsonpath-ng, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.13.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 jsonpath-ng-1.14.0 mitogen-0.3.54 tornado-6.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n	0	b2435a90-62d2-4792-be8c-7ed76b2004a8
ae465000-bace-495e-b3a6-8c4519f536af	2026-10-28 11:23:30.787438+00	2026-10-28 11:23:31.81623+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp8kedzeco --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.027 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.034 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.088 seconds\ncompiler       DEBUG   The entire export command took 0.172 seconds\n	0	b2435a90-62d2-4792-be8c-7ed76b2004a8
8db743de-a4d2-4a18-b35a-6fb64401277a	2026-10-28 11:23:32.039161+00	2026-10-28 11:23:32.065068+00		Init		Using extra environment variables during compile \n	0	241de1e7-60f3-44b9-a62e-99294e0ee99b
1401ad46-882c-4357-98a1-15ccac064b37	2026-10-28 11:23:32.074805+00	2026-10-28 11:23:32.0949+00		Venv check		Creating new venv at /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env-py3.14\n	0	241de1e7-60f3-44b9-a62e-99294e0ee99b
0213e6a4-5286-4fa2-8840-9a05c869ba81	2026-10-28 11:23:39.32416+00	2026-10-28 11:23:40.272843+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmppo_6pyfe --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.027 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.036 seconds\ncompiler       DEBUG   The entire export command took 0.095 seconds\n	0	0b0626a3-391c-4715-b548-ecf5f312dd23
723465fa-d9d3-4309-b068-ac61827ce5d7	2026-10-28 11:23:41.648356+00	2026-10-28 11:23:41.863179+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	63791996-051a-43de-a3c3-f538b5149696
e598d8c2-7447-4e93-a550-2218dde0a24c	2026-10-28 11:23:32.108199+00	2026-10-28 11:23:32.322553+00	/tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 21.0.0.dev0\nNot uninstalling inmanta-core at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	241de1e7-60f3-44b9-a62e-99294e0ee99b
43ff3584-0f73-4744-abbc-5fc7806237e9	2026-10-28 11:23:39.272303+00	2026-10-28 11:23:39.291664+00		Init		Using extra environment variables during compile \n	0	0b0626a3-391c-4715-b548-ecf5f312dd23
bc4307f2-5391-4599-9150-f12cc6547e39	2026-10-28 11:23:40.472912+00	2026-10-28 11:23:40.494666+00		Init		Using extra environment variables during compile \n	0	c0e588cc-d217-4a0b-b26f-f6564e9b0a16
c2e1032f-a7bb-487b-8b82-425a087e89b2	2026-10-28 11:23:39.299544+00	2026-10-28 11:23:39.316038+00		Venv check		Found existing venv\n	0	0b0626a3-391c-4715-b548-ecf5f312dd23
cb0f7672-0cc0-4e2e-a793-8755d0a75358	2026-10-28 11:23:40.530359+00	2026-10-28 11:23:41.46958+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp3nq8379w --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.027 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.039 seconds\ncompiler       DEBUG   The entire export command took 0.097 seconds\n	0	c0e588cc-d217-4a0b-b26f-f6564e9b0a16
a4b8a8f0-bcf3-4674-8235-dad4c36b7dd1	2026-10-28 11:23:40.503335+00	2026-10-28 11:23:40.520835+00		Venv check		Found existing venv\n	0	c0e588cc-d217-4a0b-b26f-f6564e9b0a16
922342a2-da43-4012-aa68-c15881259e46	2026-10-28 11:23:41.587167+00	2026-10-28 11:23:41.608347+00		Init		Using extra environment variables during compile \n	0	63791996-051a-43de-a3c3-f538b5149696
efa1d13b-06f2-40d7-879b-c63d4d4417ac	2026-10-28 11:23:41.6168+00	2026-10-28 11:23:41.635053+00		Venv check		Found existing venv\n	0	63791996-051a-43de-a3c3-f538b5149696
350ef1f2-d55f-4476-b29e-ec1a3911b62a	2026-10-28 11:23:37.917643+00	2026-10-28 11:23:37.934081+00		Venv check		Found existing venv\n	0	685b8eb0-cf59-407c-94a7-9639122a6058
1e6fa9f0-0d86-4567-bc4c-0f9f862bf7e0	2026-10-28 11:23:37.942479+00	2026-10-28 11:23:38.930529+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmp20bs9g26 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.035 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.075 seconds\ncompiler       DEBUG   The entire export command took 0.141 seconds\n	0	685b8eb0-cf59-407c-94a7-9639122a6058
412dd7c6-bdc0-4fa5-a35b-7b32df9aee56	2026-10-28 11:23:36.756094+00	2026-10-28 11:23:37.742295+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpyiulf1a_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.005 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.031 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.070 seconds\ncompiler       DEBUG   The entire export command took 0.134 seconds\n	0	859d28b7-c34d-4373-a750-fe408024683d
98e7a12a-d4a4-4fb8-b8ef-126e824cb7cf	2026-10-28 11:23:37.891237+00	2026-10-28 11:23:37.909719+00		Init		Using extra environment variables during compile add_one_resource='true'\n	0	685b8eb0-cf59-407c-94a7-9639122a6058
68200676-d975-4315-90a2-c64fd12a5bad	2026-10-28 11:23:46.952084+00	2026-10-28 11:23:46.975265+00		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmp56oemexw/server/427218da-a7a5-4aed-a950-2b6c55ffbd14/compiler and no repository set.\n	1	97b06af4-dddb-4d3e-ac52-382ec7415f0e
aea221fd-38bb-4aaf-b3c7-3cf6edc2cfb8	2026-10-28 11:23:35.424097+00	2026-10-28 11:23:36.388947+00	/tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6d05d33c-20da-450d-8ba3-e651c83aeda3 --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpklfzgb5_ --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 7.0.0\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int, offset: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: list, index: int) -> any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: list) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: any, no_unknown: bool) -> any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.008 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.028 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=0 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.066 seconds\ncompiler       DEBUG   The entire export command took 0.124 seconds\n	0	241de1e7-60f3-44b9-a62e-99294e0ee99b
6e1d0f57-bfe5-4741-ab00-2d904aba5041	2026-10-28 11:23:32.330095+00	2026-10-28 11:23:35.406663+00	/tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpy4523sj5:\n                                 Pip command: /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpy4523sj5 inmanta-module-fs inmanta-module-mitogen inmanta-module-std<8 inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Collecting inmanta-module-fs\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl.metadata (499 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl.metadata (187 bytes)\ninmanta.pip              DEBUG   Collecting inmanta-module-std<8\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl.metadata (224 bytes)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.5.10)\ninmanta.pip              DEBUG   Collecting tornado>6.5 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl.metadata (2.6 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.13.0)\ninmanta.pip              DEBUG   Collecting jsonpath-ng~=1.7 (from inmanta-core==21.0.0.dev0)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.14.0-py3-none-any.whl.metadata (17 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl.metadata (2.2 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Using cached inmanta_module_std-7.0.0-py3-none-any.whl (19 kB)\ninmanta.pip              DEBUG   Using cached jsonpath_ng-1.14.0-py3-none-any.whl (84 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_fs-1.2.0-py3-none-any.whl (13 kB)\ninmanta.pip              DEBUG   Using cached inmanta_module_mitogen-0.2.5-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Using cached tornado-6.6-cp311-abi3-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl (529 kB)\ninmanta.pip              DEBUG   Using cached mitogen-0.3.54-py2.py3-none-any.whl (294 kB)\ninmanta.pip              DEBUG   Installing collected packages: tornado, mitogen, jsonpath-ng, inmanta-module-std, inmanta-module-mitogen, inmanta-module-fs\ninmanta.pip              DEBUG   Attempting uninstall: tornado\ninmanta.pip              DEBUG   Found existing installation: tornado 6.5.10\ninmanta.pip              DEBUG   Not uninstalling tornado at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'tornado'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: jsonpath-ng\ninmanta.pip              DEBUG   Found existing installation: jsonpath-ng 1.13.0\ninmanta.pip              DEBUG   Not uninstalling jsonpath-ng at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'jsonpath-ng'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-std\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-std 8.7.5\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-std at /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib/python3.14/site-packages, outside environment /tmp/tmp56oemexw/server/6d05d33c-20da-450d-8ba3-e651c83aeda3/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-std'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   Successfully installed inmanta-module-fs-1.2.0 inmanta-module-mitogen-0.2.5 inmanta-module-std-7.0.0 jsonpath-ng-1.14.0 mitogen-0.3.54 tornado-6.6\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + fs: 1.2.0\n                                 + mitogen: 0.2.5\n                                 + std: 7.0.0\n                                 - std: 8.7.5\n	0	241de1e7-60f3-44b9-a62e-99294e0ee99b
3446f943-9c3c-43d5-a69a-541ff4ee1029	2026-10-28 11:23:36.694634+00	2026-10-28 11:23:36.718806+00		Init		Using extra environment variables during compile \n	0	859d28b7-c34d-4373-a750-fe408024683d
39e1a1a5-9549-492a-a91b-af8910578a0f	2026-10-28 11:23:36.727993+00	2026-10-28 11:23:36.746725+00		Venv check		Found existing venv\n	0	859d28b7-c34d-4373-a750-fe408024683d
fc8c5595-3758-4de8-b672-431c79e44be9	2026-10-28 11:23:44.634777+00	2026-10-28 11:23:45.567912+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 6c727c98-6b55-4b9d-827d-dc48c90136ca --server_address localhost --server_port 34053 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp4xkby00e --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.004 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.009 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.2.0\ncompiler       INFO      mitogen: 0.2.5\ncompiler       INFO      std: 8.7.5\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::dict_keys(dct: dict[string, any]) -> string[]\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.009 seconds\ncompiler       DEBUG   Compile done\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/reserve_version\nexporter       INFO    Ignoring resource of type std::AgentConfig because it requested to ignore it. (location: ./main.cf:4)\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.027 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:34053/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=0 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:34053/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.037 seconds\ncompiler       DEBUG   The entire export command took 0.095 seconds\n	0	63791996-051a-43de-a3c3-f538b5149696
bc34aaed-4930-4573-98ca-139ed924ffbb	2026-10-28 11:23:41.871067+00	2026-10-28 11:23:44.617+00	/tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 mitogen: 0.2.5\n                                 fs: 1.2.0\n                                 std: 8.7.5\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpvr50d_j1:\n                                 Pip command: /tmp/tmp56oemexw/server/6c727c98-6b55-4b9d-827d-dc48c90136ca/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpvr50d_j1 inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-core==21.0.0.dev0\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in ./.env/lib64/python3.14/site-packages (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (8.7.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib64/python3.14/site-packages (0.2.5)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==21.0.0.dev0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (21.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.32.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.6,>=8.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (8.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.12.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.7.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<51,>=36 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (50.0.2)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.19,>=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.18.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<12,>=8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (11.2.1)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<26.4,>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (26.2.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.14.1)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.7.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado>6.5 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (6.6)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.19.1)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.3.8)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql<0.337,>=0.318.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.336.2)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper<0.10,>=0.8 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4,>=3.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (3.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in ./.env/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (1.14.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests[use_chardet_on_py3] in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from inmanta-core==21.0.0.dev0) (2.34.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from build~=1.0->inmanta-core==21.0.0.dev0) (1.3.3)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (9.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (15.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cryptography<51,>=36->inmanta-core==21.0.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (2.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from email-validator<3,>=1->inmanta-core==21.0.0.dev0) (3.20)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from jinja2~=3.0->inmanta-core==21.0.0.dev0) (3.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.50.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (2.50.1)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.16.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (4.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.4 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==21.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-dateutil~=2.0->inmanta-core==21.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cross-web>=0.6.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-graphql<0.337,>=0.318.1->inmanta-core==21.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (3.5.6)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from strawberry-sqlalchemy-mapper<0.10,>=0.8->inmanta-core==21.0.0.dev0) (2.0.1787969905)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from typing_inspect~=0.9->inmanta-core==21.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib64/python3.14/site-packages (from inmanta-module-mitogen) (0.3.54)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from cffi>=2.0.0->cryptography<51,>=36->inmanta-core==21.0.0.dev0) (3.12)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (3.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.26 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2023.5.7 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (2026.10.23)\ninmanta.pip              DEBUG   Requirement already satisfied: tzdata in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2026.6)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet<8,>=3.0.2 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from requests[use_chardet_on_py3]->inmanta-core==21.0.0.dev0) (7.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (4.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (2.21.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/jp/Inmanta/research/undeployable-columns-2026-10-28/venv-core/lib64/python3.14/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==21.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	63791996-051a-43de-a3c3-f538b5149696
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d5e30aa4-8674-4019-88f1-1150b432d839
6d05d33c-20da-450d-8ba3-e651c83aeda3	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": false, "report_only": false, "receive_events": true, "purge_on_delete": false}	7ecdc9fdf36cb2fd358f08900eed405b	std::AgentConfig	localhost	f	1c4976f3-9144-4b03-8d64-de364300d79f
6d05d33c-20da-450d-8ba3-e651c83aeda3	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	1c4976f3-9144-4b03-8d64-de364300d79f
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	d2f88819-e69e-4490-a94f-2b84654a210d
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	0c7f8f50-5fd9-4657-a4d9-ed8348e796f6
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28a6be28c87f4e90c3d19f772cc6eb93	fs::File	/tmp/test_orphan	f	0c7f8f50-5fd9-4657-a4d9-ed8348e796f6
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	9e8afb96-35ad-4f1a-907f-8a08e611abdd
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	64c48ff5-d8c2-41e9-ac58-7c79dde65e00
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	bb421cee-9334-43dd-9d1b-de05dce67c6b
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	5000b8a5-a95e-4aeb-a3c3-2d01fa419b38
6c727c98-6b55-4b9d-827d-dc48c90136ca	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	8fb6c695-7278-483e-8374-1340fab8a8b5
6c727c98-6b55-4b9d-827d-dc48c90136ca	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	c111c1c0-75ce-4fdf-8785-47872a5c9f34
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "content": null, "mutators": [], "requires": [], "references": [], "send_event": true, "permissions": 644, "report_only": false, "receive_events": true, "purge_on_delete": false}	28b181a98279db3c2d85305e0c4d43c6	fs::File	/tmp/test	f	642a840b-4085-4fd6-b26b-71586afa83bc
6c727c98-6b55-4b9d-827d-dc48c90136ca	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	e63ed15a-271b-4914-af3d-540bc5aa790b
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key10]	agent1	{"key": "key10", "value": "val10", "purged": false, "requires": [], "send_event": true, "report_only": true}	a060d3943ce7843d7df5937d47b21669	test::Resource	key10	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key11]	agent1	{"key": "key11", "value": "val11", "purged": false, "requires": [], "send_event": true, "report_only": true}	c31940c3067584e6fcf87bcd660834be	test::Resource	key11	f	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	32f22e02-f117-4318-b5b7-424d894616be
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	32f22e02-f117-4318-b5b7-424d894616be
\.


--
-- Data for Name: resource_diff; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_diff (id, environment, resource_id, diff, created) FROM stdin;
388b19df-7935-444a-a80d-73287a689d65	336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key10]	{"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}	2026-10-28 11:23:46.544738+00
a4738035-7104-40b2-af5d-e5f6b395704c	336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key11]	{"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}	2026-10-28 11:23:46.573309+00
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_handler_run_at, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, last_handler_run, blocked, is_deploying, created, last_handler_run_compliant, non_compliant_diff, orphaned_after) FROM stdin;
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Fail[agent1,key=key2]	2026-10-28 11:23:46.145223+00	\N	2026-10-28 11:23:46.145223+00	fa7087083326c953261c388f13f3df3c	1	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:46.106296+00	f	\N	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test]	2026-10-28 11:23:31.904656+00	\N	2026-10-28 11:23:31.904656+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:31.874616+00	f	\N	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key10]	2026-10-28 11:23:46.544738+00	\N	2026-10-28 11:23:46.544738+00	a060d3943ce7843d7df5937d47b21669	2	non_compliant	test::Resource	agent1	key10	a060d3943ce7843d7df5937d47b21669	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.438116+00	f	388b19df-7935-444a-a80d-73287a689d65	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key1]	2026-10-28 11:23:46.183853+00	2026-10-28 11:23:46.160114+00	2026-10-28 11:23:46.183853+00	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.106296+00	t	\N	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	std::AgentConfig[internal,agentname=localhost]	2026-10-28 11:23:36.544357+00	\N	2026-10-28 11:23:36.544357+00	7ecdc9fdf36cb2fd358f08900eed405b	1	unavailable	std::AgentConfig	internal	localhost	7ecdc9fdf36cb2fd358f08900eed405b	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:36.503977+00	f	\N	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key3]	2026-10-28 11:23:46.210565+00	\N	2026-10-28 11:23:46.210565+00	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	SKIPPED	NOT_BLOCKED	f	2026-10-28 11:23:46.106296+00	f	\N	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	fs::File[localhost,path=/tmp/test]	2026-10-28 11:23:36.590612+00	\N	2026-10-28 11:23:36.590612+00	28b181a98279db3c2d85305e0c4d43c6	1	unavailable	fs::File	localhost	/tmp/test	28b181a98279db3c2d85305e0c4d43c6	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:36.503977+00	f	\N	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key11]	2026-10-28 11:23:46.573309+00	\N	2026-10-28 11:23:46.573309+00	c31940c3067584e6fcf87bcd660834be	2	non_compliant	test::Resource	agent1	key11	c31940c3067584e6fcf87bcd660834be	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.438116+00	f	a4738035-7104-40b2-af5d-e5f6b395704c	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	fs::File[localhost,path=/tmp/test_orphan]	2026-10-28 11:23:39.137643+00	\N	2026-10-28 11:23:39.137643+00	28a6be28c87f4e90c3d19f772cc6eb93	3	unavailable	fs::File	localhost	/tmp/test_orphan	28a6be28c87f4e90c3d19f772cc6eb93	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:39.098251+00	f	\N	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key7]	2026-10-28 11:23:46.594599+00	2026-10-28 11:23:46.581724+00	2026-10-28 11:23:46.594599+00	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.438116+00	t	\N	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	test::Resource[agent2,key=key2]	2026-10-28 11:23:45.741407+00	\N	2026-10-28 11:23:45.741407+00	509af84c7d978674472e11ce2cad1b8b	7	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:45.716283+00	f	\N	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	test::Resource[agent3,key=key3]	2026-10-28 11:23:45.750348+00	\N	2026-10-28 11:23:45.750348+00	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	FAILED	NOT_BLOCKED	f	2026-10-28 11:23:45.716283+00	f	\N	7
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	NEW	BLOCKED	f	2026-10-28 11:23:46.106296+00	\N	\N	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	NEW	BLOCKED	f	2026-10-28 11:23:46.106296+00	\N	\N	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key6]	2026-10-28 11:23:46.247411+00	2026-10-28 11:23:46.223017+00	2026-10-28 11:23:46.247411+00	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.106296+00	t	\N	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	test::Resource[agent1,key=key9]	2026-10-28 11:23:46.506369+00	2026-10-28 11:23:46.476739+00	2026-10-28 11:23:46.506369+00	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	SUCCESSFUL	NOT_BLOCKED	f	2026-10-28 11:23:46.438116+00	t	\N	\N
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	d5e30aa4-8674-4019-88f1-1150b432d839	\N
6d05d33c-20da-450d-8ba3-e651c83aeda3	1c4976f3-9144-4b03-8d64-de364300d79f	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	d2f88819-e69e-4490-a94f-2b84654a210d	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	0c7f8f50-5fd9-4657-a4d9-ed8348e796f6	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	9e8afb96-35ad-4f1a-907f-8a08e611abdd	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	64c48ff5-d8c2-41e9-ac58-7c79dde65e00	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	bb421cee-9334-43dd-9d1b-de05dce67c6b	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	5000b8a5-a95e-4aeb-a3c3-2d01fa419b38	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	8fb6c695-7278-483e-8374-1340fab8a8b5	set-a
6c727c98-6b55-4b9d-827d-dc48c90136ca	c111c1c0-75ce-4fdf-8785-47872a5c9f34	set-b
6c727c98-6b55-4b9d-827d-dc48c90136ca	642a840b-4085-4fd6-b26b-71586afa83bc	\N
6c727c98-6b55-4b9d-827d-dc48c90136ca	e63ed15a-271b-4914-af3d-540bc5aa790b	set-a
336135a6-cee1-4a5c-81f8-dbda19ed9801	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	57668439-0d2f-40d6-8aa9-d79e8554dd7c	\N
336135a6-cee1-4a5c-81f8-dbda19ed9801	32f22e02-f117-4318-b5b7-424d894616be	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	1	d5e30aa4-8674-4019-88f1-1150b432d839
6d05d33c-20da-450d-8ba3-e651c83aeda3	1	1c4976f3-9144-4b03-8d64-de364300d79f
6c727c98-6b55-4b9d-827d-dc48c90136ca	2	d2f88819-e69e-4490-a94f-2b84654a210d
6c727c98-6b55-4b9d-827d-dc48c90136ca	3	0c7f8f50-5fd9-4657-a4d9-ed8348e796f6
6c727c98-6b55-4b9d-827d-dc48c90136ca	4	9e8afb96-35ad-4f1a-907f-8a08e611abdd
6c727c98-6b55-4b9d-827d-dc48c90136ca	5	64c48ff5-d8c2-41e9-ac58-7c79dde65e00
6c727c98-6b55-4b9d-827d-dc48c90136ca	6	bb421cee-9334-43dd-9d1b-de05dce67c6b
6c727c98-6b55-4b9d-827d-dc48c90136ca	7	5000b8a5-a95e-4aeb-a3c3-2d01fa419b38
6c727c98-6b55-4b9d-827d-dc48c90136ca	7	8fb6c695-7278-483e-8374-1340fab8a8b5
6c727c98-6b55-4b9d-827d-dc48c90136ca	7	c111c1c0-75ce-4fdf-8785-47872a5c9f34
6c727c98-6b55-4b9d-827d-dc48c90136ca	8	642a840b-4085-4fd6-b26b-71586afa83bc
6c727c98-6b55-4b9d-827d-dc48c90136ca	8	e63ed15a-271b-4914-af3d-540bc5aa790b
336135a6-cee1-4a5c-81f8-dbda19ed9801	1	6bbf54ea-dbc4-4416-932f-33a7e0bc7f94
336135a6-cee1-4a5c-81f8-dbda19ed9801	2	57668439-0d2f-40d6-8aa9-d79e8554dd7c
336135a6-cee1-4a5c-81f8-dbda19ed9801	3	32f22e02-f117-4318-b5b7-424d894616be
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
2f4f0ce2-dc93-44c8-9adf-f55f0892d6b8	store	2026-10-28 11:23:31.747484+00	2026-10-28 11:23:31.764003+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-28T11:23:31.764018+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	1	{"fs::File[localhost,path=/tmp/test],v=1"}
28a09149-e26e-4a83-a502-a502ab75eb06	deploy	2026-10-28 11:23:31.88933+00	2026-10-28 11:23:31.904656+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:31.903701+00:00\\"}"}	unavailable	\N	nochange	6c727c98-6b55-4b9d-827d-dc48c90136ca	1	{"fs::File[localhost,path=/tmp/test],v=1"}
01a1417b-0bca-4c2b-a801-f275b24b80eb	store	2026-10-28 11:23:36.32657+00	2026-10-28 11:23:36.352043+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-28T11:23:36.352075+00:00\\"}"}	\N	\N	\N	6d05d33c-20da-450d-8ba3-e651c83aeda3	1	{"fs::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
282713e6-d90c-425a-bcc2-5cfcd66df023	deploy	2026-10-28 11:23:36.527695+00	2026-10-28 11:23:36.544357+00	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:36.542267+00:00\\"}"}	unavailable	\N	nochange	6d05d33c-20da-450d-8ba3-e651c83aeda3	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
494df248-0979-4c19-9ff6-77c4841e63a8	deploy	2026-10-28 11:23:36.575018+00	2026-10-28 11:23:36.590612+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:36.589025+00:00\\"}"}	unavailable	\N	nochange	6d05d33c-20da-450d-8ba3-e651c83aeda3	1	{"fs::File[localhost,path=/tmp/test],v=1"}
a5404ddf-62bb-4e3d-b178-15b79d1e664e	store	2026-10-28 11:23:37.667121+00	2026-10-28 11:23:37.685702+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-28T11:23:37.685724+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	2	{"fs::File[localhost,path=/tmp/test],v=2"}
6420cba8-10ff-4fbb-90b5-04a66b281d86	store	2026-10-28 11:23:38.873193+00	2026-10-28 11:23:38.885808+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-28T11:23:38.885830+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3"}
94f5f280-4afa-4f6e-9805-a06484b8be64	deploy	2026-10-28 11:23:39.120424+00	2026-10-28 11:23:39.137643+00	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2026-10-28T11:23:39.136060+00:00\\"}"}	unavailable	\N	nochange	6c727c98-6b55-4b9d-827d-dc48c90136ca	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
9f7d92e9-13ac-45f7-add8-3e0b202cad5b	store	2026-10-28 11:23:40.223881+00	2026-10-28 11:23:40.231373+00	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2026-10-28T11:23:40.231392+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	4	{"fs::File[localhost,path=/tmp/test],v=4"}
20059498-d8d1-4f33-a1ff-e2f7faa029f1	store	2026-10-28 11:23:41.421344+00	2026-10-28 11:23:41.429703+00	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2026-10-28T11:23:41.429729+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	5	{"fs::File[localhost,path=/tmp/test],v=5"}
9c8000a1-f08b-4e5b-8e30-7197843ea568	store	2026-10-28 11:23:45.522142+00	2026-10-28 11:23:45.527664+00	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2026-10-28T11:23:45.527685+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	6	{"fs::File[localhost,path=/tmp/test],v=6"}
7a45e9f9-d821-4374-ae5b-51aa9f2da065	store	2026-10-28 11:23:45.669175+00	2026-10-28 11:23:45.677697+00	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2026-10-28T11:23:45.677713+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	7	{"fs::File[localhost,path=/tmp/test],v=7","test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7"}
09d45bd1-b8b6-4aae-b87a-ffd462f63676	deploy	2026-10-28 11:23:45.729048+00	2026-10-28 11:23:45.741407+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2026-10-28T11:23:45.740770+00:00\\"}"}	unavailable	\N	nochange	6c727c98-6b55-4b9d-827d-dc48c90136ca	7	{"test::Resource[agent2,key=key2],v=7"}
a1f7eb7a-b554-424c-812a-ff228aa0e235	deploy	2026-10-28 11:23:45.741478+00	2026-10-28 11:23:45.750348+00	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2026-10-28T11:23:45.749441+00:00\\"}"}	unavailable	\N	nochange	6c727c98-6b55-4b9d-827d-dc48c90136ca	7	{"test::Resource[agent3,key=key3],v=7"}
26492702-78e3-4709-b56b-0c1a97cf961a	store	2026-10-28 11:23:45.852714+00	2026-10-28 11:23:45.856648+00	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2026-10-28T11:23:45.856657+00:00\\"}"}	\N	\N	\N	6c727c98-6b55-4b9d-827d-dc48c90136ca	8	{"fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
77c5962c-ef48-484d-8f1a-c3e8d57c9030	store	2026-10-28 11:23:46.093526+00	2026-10-28 11:23:46.096337+00	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2026-10-28T11:23:46.096347+00:00\\"}"}	\N	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key3],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key1],v=1","test::Fail[agent1,key=key2],v=1"}
b5b43bda-d359-4bb4-958f-55b15a8563f6	deploy	2026-10-28 11:23:46.120612+00	2026-10-28 11:23:46.145223+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 4940edc1-84de-4d7f-820b-0862f00120e9).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"4940edc1-84de-4d7f-820b-0862f00120e9\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.140531+00:00\\"}","{\\"msg\\": \\"An error occurred during deployment of test::Fail[agent1,key=key2] (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/jp/Inmanta/research/undeployable-columns-2026-10-28/core/src/inmanta/agent/handler.py\\\\\\", line 909, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^\\\\n  File \\\\\\"/home/jp/Inmanta/research/undeployable-columns-2026-10-28/core/tests/conftest.py\\\\\\", line 2655, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2]\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.143060+00:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1. (deploy_id: 4940edc1-84de-4d7f-820b-0862f00120e9) - duration: 0.0044 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"duration\\": 0.004359722137451172, \\"deploy_id\\": \\"4940edc1-84de-4d7f-820b-0862f00120e9\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.145090+00:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}, "purged": {"current": true, "desired": false}}}	nochange	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Fail[agent1,key=key2],v=1"}
e3111e00-3acc-4e5e-9211-a8d8407fbdbf	deploy	2026-10-28 11:23:46.160264+00	2026-10-28 11:23:46.183853+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 0f50d528-4cd9-43a9-be1d-e4946cfdae99).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"0f50d528-4cd9-43a9-be1d-e4946cfdae99\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.172503+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1. (deploy_id: 0f50d528-4cd9-43a9-be1d-e4946cfdae99) - duration: 0.0111 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"duration\\": 0.011053800582885742, \\"deploy_id\\": \\"0f50d528-4cd9-43a9-be1d-e4946cfdae99\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.183750+00:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}, "purged": {"current": true, "desired": false}}}	created	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key1],v=1"}
d2a93349-1d73-4836-9992-82374bdd6619	deploy	2026-10-28 11:23:46.1971+00	2026-10-28 11:23:46.210565+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 446d142e-2dc0-483b-8bc1-7e835e15a4a1).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"446d142e-2dc0-483b-8bc1-7e835e15a4a1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.209543+00:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.209962+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1. (deploy_id: 446d142e-2dc0-483b-8bc1-7e835e15a4a1) - duration: 0.0007 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"duration\\": 0.0006930828094482422, \\"deploy_id\\": \\"446d142e-2dc0-483b-8bc1-7e835e15a4a1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.210449+00:00\\"}"}	skipped	\N	nochange	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key3],v=1"}
bad41965-4d64-44c2-8531-1a174f16c3e1	deploy	2026-10-28 11:23:46.22315+00	2026-10-28 11:23:46.247411+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 0422ef36-f837-4040-8896-ccf9839f7624).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"0422ef36-f837-4040-8896-ccf9839f7624\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.236278+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1. (deploy_id: 0422ef36-f837-4040-8896-ccf9839f7624) - duration: 0.0109 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"duration\\": 0.010865449905395508, \\"deploy_id\\": \\"0422ef36-f837-4040-8896-ccf9839f7624\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.247306+00:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}, "purged": {"current": true, "desired": false}}}	created	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key6],v=1"}
cb12a4c2-677e-4d1a-af6e-78c670cf8632	store	2026-10-28 11:23:46.415659+00	2026-10-28 11:23:46.425457+00	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2026-10-28T11:23:46.425473+00:00\\"}"}	\N	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	2	{"test::Resource[agent1,key=key11],v=2","test::Resource[agent1,key=key10],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key5],v=2","test::Resource[agent1,key=key7],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key4],v=2"}
0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	store	2026-10-28 11:23:46.72578+00	2026-10-28 11:23:46.728406+00	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2026-10-28T11:23:46.728417+00:00\\"}"}	\N	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	3	{"test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key7],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key4],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key3],v=3"}
f0da6f9d-2c00-4a85-a12f-e15988222db2	dryrun	2026-10-28 11:23:46.410032+00	2026-10-28 11:23:46.411445+00	{"{\\"msg\\": \\"Running dryrun for test::Fail[agent1,key=key2],v=1 dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.410223+00:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Fail[agent1,key=key2],v=1. dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b - duration 0.0010 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0009598731994628906, \\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Fail[agent1,key=key2],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.411377+00:00\\"}"}	dry	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Fail[agent1,key=key2],v=1"}
5eaa0a7f-636e-4754-8f92-ad2a108a4ec7	dryrun	2026-10-28 11:23:46.439765+00	2026-10-28 11:23:46.440275+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key1],v=1 dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.439857+00:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key1],v=1. dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b - duration 0.0003 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0003185272216796875, \\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key1],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.440250+00:00\\"}"}	dry	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key1],v=1"}
54f401d6-6ceb-4a4b-8688-876b29ea24f7	deploy	2026-10-28 11:23:46.476881+00	2026-10-28 11:23:46.506369+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 971c1c91-b8b7-4763-bb3b-e34f622d5364).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"971c1c91-b8b7-4763-bb3b-e34f622d5364\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.489281+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2. (deploy_id: 971c1c91-b8b7-4763-bb3b-e34f622d5364) - duration: 0.0167 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"duration\\": 0.016690492630004883, \\"deploy_id\\": \\"971c1c91-b8b7-4763-bb3b-e34f622d5364\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.506212+00:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}, "purged": {"current": true, "desired": false}}}	created	336135a6-cee1-4a5c-81f8-dbda19ed9801	2	{"test::Resource[agent1,key=key9],v=2"}
9adfb19a-c26c-4e1e-9628-c2e0a3293820	deploy	2026-10-28 11:23:46.519866+00	2026-10-28 11:23:46.544738+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: a4d124ce-52e3-4115-b24d-a1d1047c5cba).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key10\\"}, \\"deploy_id\\": \\"a4d124ce-52e3-4115-b24d-a1d1047c5cba\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.532559+00:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key10] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val10\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key10]\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.533313+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key10],v=2. (deploy_id: a4d124ce-52e3-4115-b24d-a1d1047c5cba) - duration: 0.0118 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key10],v=2\\", \\"duration\\": 0.011796236038208008, \\"deploy_id\\": \\"a4d124ce-52e3-4115-b24d-a1d1047c5cba\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.544591+00:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key10],v=2": {"value": {"current": null, "desired": "val10"}, "purged": {"current": true, "desired": false}}}	nochange	336135a6-cee1-4a5c-81f8-dbda19ed9801	2	{"test::Resource[agent1,key=key10],v=2"}
d0e23ae8-dab5-469b-8c5c-a02bba980c20	deploy	2026-10-28 11:23:46.55876+00	2026-10-28 11:23:46.573309+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: 967b228f-3af0-4b17-844b-fcb3f12bec63).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key11\\"}, \\"deploy_id\\": \\"967b228f-3af0-4b17-844b-fcb3f12bec63\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.567775+00:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key11] was marked as non-compliant.\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"changes\\": {\\"value\\": {\\"current\\": null, \\"desired\\": \\"val11\\"}, \\"purged\\": {\\"current\\": true, \\"desired\\": false}}, \\"resource_id\\": \\"test::Resource[agent1,key=key11]\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.568086+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key11],v=2. (deploy_id: 967b228f-3af0-4b17-844b-fcb3f12bec63) - duration: 0.0054 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key11],v=2\\", \\"duration\\": 0.005382061004638672, \\"deploy_id\\": \\"967b228f-3af0-4b17-844b-fcb3f12bec63\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.573248+00:00\\"}"}	non_compliant	{"test::Resource[agent1,key=key11],v=2": {"value": {"current": null, "desired": "val11"}, "purged": {"current": true, "desired": false}}}	nochange	336135a6-cee1-4a5c-81f8-dbda19ed9801	2	{"test::Resource[agent1,key=key11],v=2"}
57b6e761-c74d-41fc-8e39-571c5e5258a2	deploy	2026-10-28 11:23:46.581766+00	2026-10-28 11:23:46.594599+00	{"{\\"msg\\": \\"Start run because a new version was released (deploy_id: b4116c49-1e3b-4f63-8614-898f80b1d6fb).\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"b4116c49-1e3b-4f63-8614-898f80b1d6fb\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.589966+00:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2. (deploy_id: b4116c49-1e3b-4f63-8614-898f80b1d6fb) - duration: 0.0045 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"duration\\": 0.004460334777832031, \\"deploy_id\\": \\"b4116c49-1e3b-4f63-8614-898f80b1d6fb\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.594531+00:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}, "purged": {"current": true, "desired": false}}}	created	336135a6-cee1-4a5c-81f8-dbda19ed9801	2	{"test::Resource[agent1,key=key7],v=2"}
a7a25d36-a51c-4920-8bcc-f12d5498dfcb	dryrun	2026-10-28 11:23:46.604353+00	2026-10-28 11:23:46.605169+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key3],v=1 dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.604531+00:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key3],v=1. dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b - duration 0.0005 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.00045871734619140625, \\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.605127+00:00\\"}"}	dry	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key3],v=1"}
9fc9c226-f886-4e53-9976-25a49b2b06bd	dryrun	2026-10-28 11:23:46.623868+00	2026-10-28 11:23:46.624873+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key5],v=1 dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.624007+00:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key5],v=1. dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006153583526611328, \\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key5],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.624809+00:00\\"}"}	dry	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key5],v=1"}
4e607358-1d81-4c83-a4d3-e4754368382b	dryrun	2026-10-28 11:23:46.644494+00	2026-10-28 11:23:46.645578+00	{"{\\"msg\\": \\"Running dryrun for test::Resource[agent1,key=key6],v=1 dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.644635+00:00\\"}","{\\"msg\\": \\"Finished dryrun for test::Resource[agent1,key=key6],v=1. dry_run_id: 64f1c62d-0d21-4a76-9789-811473dc514b - duration 0.0006 s\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"duration\\": 0.0006077289581298828, \\"dry_run_id\\": \\"64f1c62d-0d21-4a76-9789-811473dc514b\\", \\"resource_id\\": \\"test::Resource[agent1,key=key6],v=1\\"}, \\"timestamp\\": \\"2026-10-28T11:23:46.645483+00:00\\"}"}	dry	\N	\N	336135a6-cee1-4a5c-81f8-dbda19ed9801	1	{"test::Resource[agent1,key=key6],v=1"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
6c727c98-6b55-4b9d-827d-dc48c90136ca	2f4f0ce2-dc93-44c8-9adf-f55f0892d6b8	fs::File[localhost,path=/tmp/test]	1
6c727c98-6b55-4b9d-827d-dc48c90136ca	28a09149-e26e-4a83-a502-a502ab75eb06	fs::File[localhost,path=/tmp/test]	1
6d05d33c-20da-450d-8ba3-e651c83aeda3	01a1417b-0bca-4c2b-a801-f275b24b80eb	fs::File[localhost,path=/tmp/test]	1
6d05d33c-20da-450d-8ba3-e651c83aeda3	01a1417b-0bca-4c2b-a801-f275b24b80eb	std::AgentConfig[internal,agentname=localhost]	1
6d05d33c-20da-450d-8ba3-e651c83aeda3	282713e6-d90c-425a-bcc2-5cfcd66df023	std::AgentConfig[internal,agentname=localhost]	1
6d05d33c-20da-450d-8ba3-e651c83aeda3	494df248-0979-4c19-9ff6-77c4841e63a8	fs::File[localhost,path=/tmp/test]	1
6c727c98-6b55-4b9d-827d-dc48c90136ca	a5404ddf-62bb-4e3d-b178-15b79d1e664e	fs::File[localhost,path=/tmp/test]	2
6c727c98-6b55-4b9d-827d-dc48c90136ca	6420cba8-10ff-4fbb-90b5-04a66b281d86	fs::File[localhost,path=/tmp/test]	3
6c727c98-6b55-4b9d-827d-dc48c90136ca	6420cba8-10ff-4fbb-90b5-04a66b281d86	fs::File[localhost,path=/tmp/test_orphan]	3
6c727c98-6b55-4b9d-827d-dc48c90136ca	94f5f280-4afa-4f6e-9805-a06484b8be64	fs::File[localhost,path=/tmp/test_orphan]	3
6c727c98-6b55-4b9d-827d-dc48c90136ca	9f7d92e9-13ac-45f7-add8-3e0b202cad5b	fs::File[localhost,path=/tmp/test]	4
6c727c98-6b55-4b9d-827d-dc48c90136ca	20059498-d8d1-4f33-a1ff-e2f7faa029f1	fs::File[localhost,path=/tmp/test]	5
6c727c98-6b55-4b9d-827d-dc48c90136ca	9c8000a1-f08b-4e5b-8e30-7197843ea568	fs::File[localhost,path=/tmp/test]	6
6c727c98-6b55-4b9d-827d-dc48c90136ca	7a45e9f9-d821-4374-ae5b-51aa9f2da065	fs::File[localhost,path=/tmp/test]	7
6c727c98-6b55-4b9d-827d-dc48c90136ca	7a45e9f9-d821-4374-ae5b-51aa9f2da065	test::Resource[agent2,key=key2]	7
6c727c98-6b55-4b9d-827d-dc48c90136ca	7a45e9f9-d821-4374-ae5b-51aa9f2da065	test::Resource[agent3,key=key3]	7
6c727c98-6b55-4b9d-827d-dc48c90136ca	09d45bd1-b8b6-4aae-b87a-ffd462f63676	test::Resource[agent2,key=key2]	7
6c727c98-6b55-4b9d-827d-dc48c90136ca	a1f7eb7a-b554-424c-812a-ff228aa0e235	test::Resource[agent3,key=key3]	7
6c727c98-6b55-4b9d-827d-dc48c90136ca	26492702-78e3-4709-b56b-0c1a97cf961a	fs::File[localhost,path=/tmp/test]	8
6c727c98-6b55-4b9d-827d-dc48c90136ca	26492702-78e3-4709-b56b-0c1a97cf961a	test::Resource[agent2,key=key2]	8
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Resource[agent1,key=key3]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Resource[agent1,key=key4]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Resource[agent1,key=key5]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Resource[agent1,key=key6]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Resource[agent1,key=key1]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	77c5962c-ef48-484d-8f1a-c3e8d57c9030	test::Fail[agent1,key=key2]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	b5b43bda-d359-4bb4-958f-55b15a8563f6	test::Fail[agent1,key=key2]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	e3111e00-3acc-4e5e-9211-a8d8407fbdbf	test::Resource[agent1,key=key1]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	d2a93349-1d73-4836-9992-82374bdd6619	test::Resource[agent1,key=key3]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	bad41965-4d64-44c2-8531-1a174f16c3e1	test::Resource[agent1,key=key6]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key11]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key10]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key9]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key5]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key7]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Fail[agent1,key=key2]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key3]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key1]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	cb12a4c2-677e-4d1a-af6e-78c670cf8632	test::Resource[agent1,key=key4]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	f0da6f9d-2c00-4a85-a12f-e15988222db2	test::Fail[agent1,key=key2]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	5eaa0a7f-636e-4754-8f92-ad2a108a4ec7	test::Resource[agent1,key=key1]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	54f401d6-6ceb-4a4b-8688-876b29ea24f7	test::Resource[agent1,key=key9]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	9adfb19a-c26c-4e1e-9628-c2e0a3293820	test::Resource[agent1,key=key10]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	d0e23ae8-dab5-469b-8c5c-a02bba980c20	test::Resource[agent1,key=key11]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	57b6e761-c74d-41fc-8e39-571c5e5258a2	test::Resource[agent1,key=key7]	2
336135a6-cee1-4a5c-81f8-dbda19ed9801	a7a25d36-a51c-4920-8bcc-f12d5498dfcb	test::Resource[agent1,key=key3]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	9fc9c226-f886-4e53-9976-25a49b2b06bd	test::Resource[agent1,key=key5]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	4e607358-1d81-4c83-a4d3-e4754368382b	test::Resource[agent1,key=key6]	1
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key5]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key7]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key1]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key8]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key4]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Fail[agent1,key=key2]	3
336135a6-cee1-4a5c-81f8-dbda19ed9801	0f4b88e0-c7d6-4aad-a3e9-eb6f38bfaf5d	test::Resource[agent1,key=key3]	3
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
6d05d33c-20da-450d-8ba3-e651c83aeda3	1
6c727c98-6b55-4b9d-827d-dc48c90136ca	8
336135a6-cee1-4a5c-81f8-dbda19ed9801	2
\.


--
-- Data for Name: schedulersession; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schedulersession (hostname, environment, first_seen, expired, sid) FROM stdin;
NOSdrive	6c727c98-6b55-4b9d-827d-dc48c90136ca	2026-10-28 11:23:24.675754+00	\N	1652e707-be62-4949-a95e-c39dac88a259
NOSdrive	6d05d33c-20da-450d-8ba3-e651c83aeda3	2026-10-28 11:23:24.817868+00	\N	74827c67-92d7-4b03-b2c1-f6cdeea6f52b
NOSdrive	336135a6-cee1-4a5c-81f8-dbda19ed9801	2026-10-28 11:23:45.926409+00	2026-10-28 11:23:46.70352+00	99b0f6fd-6ea0-46e6-a586-e7f8c38f0574
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150,202511030,202511100,202511180,202601020,202601080,202601130,202601260,202601270,202603040,202605060,202605150,202607040,202607130,202607150,202610050,202610051,202610150,202610160,202610280}
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

--\unrestrict CJMRxhNTu41sVfkXnO661KcGE3ypI4D1wBbcHg3tpp2CUUEw9G7cqh2N3mTDVZw

