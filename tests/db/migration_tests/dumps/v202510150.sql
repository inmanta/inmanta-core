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
    'skipped_for_undefined'
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
    'skipped_for_undefined'
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
    last_failover timestamp with time zone,
    paused boolean DEFAULT false,
    id_primary uuid,
    unpause_on_resume boolean
);


--
-- Name: agent_modules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_modules (
    cm_version integer NOT NULL,
    agent_name character varying NOT NULL,
    inmanta_module_name character varying NOT NULL,
    inmanta_module_version character varying NOT NULL,
    environment uuid NOT NULL
);


--
-- Name: agentinstance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentinstance (
    id uuid NOT NULL,
    process uuid NOT NULL,
    name character varying NOT NULL,
    expired timestamp with time zone,
    tid uuid NOT NULL
);


--
-- Name: agentprocess; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentprocess (
    hostname character varying NOT NULL,
    environment uuid NOT NULL,
    first_seen timestamp with time zone,
    last_seen timestamp with time zone,
    expired timestamp with time zone,
    sid uuid NOT NULL
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
    links jsonb DEFAULT '{}'::jsonb NOT NULL
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
-- Name: discoveredresource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discoveredresource (
    environment uuid NOT NULL,
    discovered_resource_id character varying NOT NULL,
    "values" jsonb NOT NULL,
    discovered_at timestamp with time zone NOT NULL,
    discovery_resource_id character varying,
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
    requirements character varying[] DEFAULT ARRAY[]::character varying[] NOT NULL
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
-- Name: resource_persistent_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resource_persistent_state (
    environment uuid NOT NULL,
    resource_id character varying NOT NULL,
    last_deploy timestamp with time zone,
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
    is_orphan boolean NOT NULL,
    last_deploy_result character varying NOT NULL,
    blocked character varying NOT NULL,
    is_deploying boolean DEFAULT false,
    created timestamp with time zone NOT NULL
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
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    installed_versions integer[]
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

COPY public.agent (environment, name, last_failover, paused, id_primary, unpause_on_resume) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	$__scheduler	2025-10-15 13:47:15.650912+02	f	1a47feab-900c-468d-bb20-5ca8c751dddb	\N
272d3692-7f7a-48c6-83b1-9f0b55db5f33	$__scheduler	\N	f	\N	\N
7b2d2696-253e-4661-8d06-c887d7adadef	localhost	\N	f	\N	\N
7b2d2696-253e-4661-8d06-c887d7adadef	internal	\N	f	\N	\N
7b2d2696-253e-4661-8d06-c887d7adadef	agent3	\N	f	\N	\N
7b2d2696-253e-4661-8d06-c887d7adadef	agent2	\N	f	\N	\N
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	agent1	\N	t	\N	t
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	$__scheduler	2025-10-15 13:48:00.359347+02	t	\N	t
610b57e2-82b5-4559-9c48-e5890d2fc34e	$__scheduler	\N	f	\N	\N
\.


--
-- Data for Name: agent_modules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_modules (cm_version, agent_name, inmanta_module_name, inmanta_module_version, environment) FROM stdin;
1	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
1	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
1	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
2	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
2	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
2	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
3	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
3	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
3	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
4	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
4	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
4	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
5	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
5	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
5	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
6	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
6	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
6	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
7	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
7	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
7	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
8	localhost	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
8	internal	std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef
8	localhost	fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
1a47feab-900c-468d-bb20-5ca8c751dddb	b2292ea2-a9bc-11f0-bcb2-8323a3f5eef2	$__scheduler	\N	7b2d2696-253e-4661-8d06-c887d7adadef
084e6c92-f64b-4bd1-8243-74f2404dce61	c98bdd88-a9bc-11f0-bcb2-8323a3f5eef2	$__scheduler	\N	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
hugo-Latitude-5421	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:15.650912+02	2025-10-15 13:48:00.348639+02	\N	b2292ea2-a9bc-11f0-bcb2-8323a3f5eef2
hugo-Latitude-5421	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2025-10-15 13:47:54.88376+02	2025-10-15 13:48:00.376246+02	\N	c98bdd88-a9bc-11f0-bcb2-8323a3f5eef2
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, requested_environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin, mergeable_environment_variables, used_environment_variables, soft_delete, links) FROM stdin;
3d2c9309-8ca2-4151-9e5f-9859ccc659c7	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:15.774062+02	2025-10-15 13:47:32.612335+02	2025-10-15 13:47:15.764919+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	f39f7ae9-8498-4ee2-bde8-0572fc113770	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}
6c933079-c5ff-4ae2-b5a2-82535ea8eeda	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:32.767797+02	2025-10-15 13:47:33.835687+02	2025-10-15 13:47:32.763956+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	2	38373d9c-dc3d-4158-ae57-86007a44c74c	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}
268e2c16-5326-4898-82a6-65ee4494f6e6	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:33.940385+02	2025-10-15 13:47:35.146555+02	2025-10-15 13:47:33.936213+02	{}	{"add_one_resource": "true"}	t	f	t	3	1c583412-6c20-4802-ae64-216a144a480f	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{"add_one_resource": "true"}	f	{}
98c1dad8-4f4a-4b4e-b67c-b51801aca758	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:35.336542+02	2025-10-15 13:47:36.678809+02	2025-10-15 13:47:35.332788+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	4	86f1a598-614b-4ee2-a867-3ecc5d4859a2	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}
a80bb043-749a-49ef-9516-c62492dbe90e	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:36.779991+02	2025-10-15 13:47:37.958515+02	2025-10-15 13:47:36.755357+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	f	t	5	d60fe5e9-fd43-43de-95a0-90ba8ab1a9ec	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}
540a4a72-9fca-457a-af8a-94d81c42a8a1	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:38.059328+02	2025-10-15 13:47:54.43554+02	2025-10-15 13:47:38.031737+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	6	307146d4-a8dd-4b96-8608-b4e59930ac2e	t	\N	{"errors": []}	f	{}	\N	\N	\N	{}	{}	f	{}
c736b649-89eb-41e4-87e7-0c7cb5832614	610b57e2-82b5-4559-9c48-e5890d2fc34e	2025-10-15 13:48:00.591977+02	2025-10-15 13:48:00.598837+02	2025-10-15 13:48:00.577257+02	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	f	\N	aa5a1d5b-775f-427a-a235-651fc84e6106	t	\N	\N	f	{}	\N	\N	\N	{}	{}	f	{}
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, version_info, total, undeployable, skipped_for_undeployable, partial_base, is_suitable_for_partial_compiles, pip_config, project_constraints) FROM stdin;
2	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2025-10-15 13:47:55.132533+02	t	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
1	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:32.395313+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
2	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:33.596129+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:34.859764+02	t	{"export_metadata": {"type": "manual", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	3	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
3	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2025-10-15 13:48:00.399663+02	f	\N	7	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
4	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:36.290275+02	t	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
5	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:37.68425+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
6	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:54.220546+02	f	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "hugo", "hostname": "hugo-Latitude-5421", "inmanta:compile:state": "success"}}	2	{}	{}	\N	t	{"pre": null, "index-url": null, "extra-index-url": [], "use-system-config": true}	
7	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:54.518052+02	t	\N	4	{}	{}	6	t	\N	\N
8	7b2d2696-253e-4661-8d06-c887d7adadef	2025-10-15 13:47:54.698686+02	t	\N	3	{}	{}	7	t	\N	\N
1	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2025-10-15 13:47:54.996458+02	t	\N	6	{"test::Resource[agent1,key=key4]"}	{"test::Resource[agent1,key=key5]"}	\N	t	\N	\N
\.


--
-- Data for Name: discoveredresource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.discoveredresource (environment, discovered_resource_id, "values", discovered_at, discovery_resource_id, resource_type, resource_id_value, agent) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	discovery::Discovered[myagent,name=discovered]	{}	2025-10-15 13:48:00.44917+02	discovery::Discovery[discovery,name=discoverer]	discovery::Discovered	discovered	myagent
7b2d2696-253e-4661-8d06-c887d7adadef	discovery::deep::submod::Dis-co-ve-red[my-agent,name=NameWithSpecial!,[::#&^@chars]	{}	2025-10-15 13:48:00.449231+02	discovery::Discovery[discovery,name=discoverer]	discovery::deep::submod::Dis-co-ve-red	NameWithSpecial!,[::#&^@chars	my-agent
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon, is_marked_for_deletion) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	dev-1	60467a26-35db-4717-9fe7-db98ea3915a5			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	8	f			f
272d3692-7f7a-48c6-83b1-9f0b55db5f33	dev-2	60467a26-35db-4717-9fe7-db98ea3915a5			{"settings": {"auto_full_compile": {"value": "", "protected": false, "protected_by": null}}}	0	f			f
610b57e2-82b5-4559-9c48-e5890d2fc34e	dev-4	60467a26-35db-4717-9fe7-db98ea3915a5			{"settings": {"server_compile": {"value": true, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "recompile_backoff": {"value": 0.1, "protected": false, "protected_by": null}}}	0	f			f
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	dev-3	60467a26-35db-4717-9fe7-db98ea3915a5			{"settings": {"auto_deploy": {"value": false, "protected": false, "protected_by": null}, "auto_full_compile": {"value": "", "protected": false, "protected_by": null}, "reset_deploy_progress_on_start": {"value": false, "protected": false, "protected_by": null}, "autostart_agent_deploy_interval": {"value": "0", "protected": false, "protected_by": null}, "autostart_agent_repair_interval": {"value": "600", "protected": false, "protected_by": null}}}	3	t			f
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
52bd7825c9c79a4bc7391ba3abf4429e3a628603	\\x2222220a436f70797269676874203230313620496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f7274206c6f6767696e670a0a66726f6d20696e6d616e746120696d706f727420646174610a66726f6d20696e6d616e74612e6167656e742e68616e646c657220696d706f7274204352554448616e646c65722c2048616e646c6572436f6e746578742c205265736f757263655075726765642c2070726f76696465720a66726f6d20696e6d616e74612e7265736f757263657320696d706f727420280a2020202049676e6f72655265736f75726365457863657074696f6e2c0a202020204d616e616765645265736f757263652c0a20202020507572676561626c655265736f757263652c0a202020207265736f757263652c0a290a0a4c4f47474552203d206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f290a0a0a407265736f7572636528227374643a3a74657374696e673a3a4e756c6c5265736f75726365222c206167656e743d226167656e746e616d65222c2069645f6174747269627574653d226e616d6522290a636c617373204e756c6c284d616e616765645265736f757263652c20507572676561626c655265736f75726365293a0a202020206669656c6473203d2028226e616d65222c20226167656e746e616d65222c20226661696c222c202276616c7565222c2022696e745f76616c756522290a0a0a407265736f7572636528227374643a3a4167656e74436f6e666967222c206167656e743d226167656e74222c2069645f6174747269627574653d226167656e746e616d6522290a636c617373204167656e74436f6e66696728507572676561626c655265736f75726365293a0a202020202222220a2020202041207265736f7572636520746861742063616e206d6f6469667920746865206167656e746d617020666f72206175746f73746172746564206167656e74730a202020202222220a0a202020206669656c6473203d2028226167656e746e616d65222c2022757269222c20226175746f737461727422290a0a20202020407374617469636d6574686f640a20202020646566206765745f6175746f7374617274286578702c206f626a293a0a20202020202020207472793a0a2020202020202020202020206966206e6f74206f626a2e6175746f73746172743a0a2020202020202020202020202020202072616973652049676e6f72655265736f75726365457863657074696f6e28290a202020202020202065786365707420457863657074696f6e3a0a20202020202020202020202023205768656e207468697320617474726962757465206973206e6f74207365742c20616c736f2069676e6f72652069740a20202020202020202020202072616973652049676e6f72655265736f75726365457863657074696f6e28290a202020202020202072657475726e206f626a2e6175746f73746172740a0a0a4070726f766964657228227374643a3a74657374696e673a3a4e756c6c5265736f75726365222c206e616d653d226e756c6c22290a636c617373204e756c6c50726f7669646572284352554448616e646c6572293a0a20202020222222446f6573206e6f7468696e6720617420616c6c2222220a0a2020202064656620726561645f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a20507572676561626c655265736f7572636529202d3e204e6f6e653a0a20202020202020206966207265736f757263652e6661696c3a0a202020202020202020202020726169736520457863657074696f6e282254686973207265736f757263652069732073657420746f206661696c22290a20202020202020206374782e646562756728224f627365727665642076616c75653a20252876616c75652973222c2076616c75653d7265736f757263652e76616c7565290a20202020202020206374782e646562756728224f6273657276656420696e742076616c75653a20252876616c75652973222c2076616c75653d7265736f757263652e696e745f76616c7565290a202020202020202072657475726e0a0a20202020646566206372656174655f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a20507572676561626c655265736f7572636529202d3e204e6f6e653a0a20202020202020206374782e7365745f6372656174656428290a0a202020206465662064656c6574655f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a20507572676561626c655265736f7572636529202d3e204e6f6e653a0a20202020202020206374782e7365745f70757267656428290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c206374783a2048616e646c6572436f6e746578742c206368616e6765733a20646963742c207265736f757263653a20507572676561626c655265736f757263650a2020202029202d3e204e6f6e653a0a20202020202020206374782e7365745f7570646174656428290a0a0a4070726f766964657228227374643a3a4167656e74436f6e666967222c206e616d653d226167656e747265737422290a636c617373204167656e74436f6e66696748616e646c6572284352554448616e646c6572293a0a0a20202020232049662074686973206576616c756174657320746f20547275652c206974206d65616e73207765206172652072756e6e696e6720616761696e737420616e2049534f202849534f382b29206f72204f53530a20202020232076657273696f6e207468617420646f65736e2774206861766520746865204155544f535441525445445f4147454e545f4d415020656e7669726f6e6d656e7420636f6e66696775726174696f6e0a2020202023206f7074696f6e20616e796d6f72652e20496e2074686174206361736520746869732068616e646c65722073686f756c64206e6f74206d616b6520616e79206368616e6765732e0a202020206861735f6175746f737461727465645f6167656e745f6d61703a20626f6f6c203d206861736174747228646174612c20224155544f53544152545f4147454e545f4d415022290a0a20202020646566205f6765745f6d61702873656c6629202d3e20646963743a0a20202020202020206465662063616c6c28293a0a20202020202020202020202072657475726e2073656c662e6765745f636c69656e7428292e6765745f73657474696e67280a202020202020202020202020202020207469643d73656c662e5f6167656e742e656e7669726f6e6d656e742c2069643d646174612e4155544f53544152545f4147454e545f4d41500a202020202020202020202020290a0a202020202020202076616c7565203d2073656c662e72756e5f73796e632863616c6c290a202020202020202072657475726e2076616c75652e726573756c745b2276616c7565225d0a0a20202020646566205f7365745f6d61702873656c662c206167656e745f636f6e6669673a206469637429202d3e204e6f6e653a0a20202020202020206465662063616c6c28293a0a20202020202020202020202072657475726e2073656c662e6765745f636c69656e7428292e7365745f73657474696e67280a202020202020202020202020202020207469643d73656c662e5f6167656e742e656e7669726f6e6d656e742c0a2020202020202020202020202020202069643d646174612e4155544f53544152545f4147454e545f4d41502c0a2020202020202020202020202020202076616c75653d6167656e745f636f6e6669672c0a202020202020202020202020290a0a202020202020202072657475726e2073656c662e72756e5f73796e632863616c6c290a0a2020202064656620726561645f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a204167656e74436f6e66696729202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e6861735f6175746f737461727465645f6167656e745f6d61703a0a2020202020202020202020206374782e696e666f280a202020202020202020202020202020206d73673d224e6f74206d616b696e6720616e79206368616e6765732c2062656361757365207765206172652072756e6e696e6720616761696e737420612076657273696f6e206f662074686520496e6d616e746120736572766572220a2020202020202020202020202020202022207468617420646f65736e277420686176652074686520746865206175746f737461727465645f6167656e745f6d617020636f6e66696775726174696f6e206f7074696f6e20616e796d6f72652e220a20202020202020202020202020202020222049742773207265636f6d6d656e64656420746f2072656d6f76652074686973207265736f757263652066726f6d2074686520636f6e66696775726174696f6e206d6f64656c2e220a202020202020202020202020290a20202020202020202020202072657475726e0a20202020202020206167656e745f636f6e666967203d2073656c662e5f6765745f6d617028290a20202020202020206374782e73657428226d6170222c206167656e745f636f6e666967290a0a20202020202020206966207265736f757263652e6167656e746e616d65206e6f7420696e206167656e745f636f6e6669673a0a2020202020202020202020207261697365205265736f7572636550757267656428290a0a20202020202020207265736f757263652e757269203d206167656e745f636f6e6669675b7265736f757263652e6167656e746e616d655d0a0a20202020646566206372656174655f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a204167656e74436f6e66696729202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e6861735f6175746f737461727465645f6167656e745f6d61703a0a20202020202020202020202072657475726e0a20202020202020206167656e745f636f6e666967203d206374782e67657428226d617022290a20202020202020206167656e745f636f6e6669675b7265736f757263652e6167656e746e616d655d203d207265736f757263652e7572690a202020202020202073656c662e5f7365745f6d6170286167656e745f636f6e666967290a0a202020206465662064656c6574655f7265736f757263652873656c662c206374783a2048616e646c6572436f6e746578742c207265736f757263653a204167656e74436f6e66696729202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e6861735f6175746f737461727465645f6167656e745f6d61703a0a20202020202020202020202072657475726e0a20202020202020206167656e745f636f6e666967203d206374782e67657428226d617022290a202020202020202064656c206167656e745f636f6e6669675b7265736f757263652e6167656e746e616d655d0a202020202020202073656c662e5f7365745f6d6170286167656e745f636f6e666967290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c206374783a2048616e646c6572436f6e746578742c206368616e6765733a20646963742c207265736f757263653a204167656e74436f6e6669670a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e6861735f6175746f737461727465645f6167656e745f6d61703a0a20202020202020202020202072657475726e0a20202020202020206167656e745f636f6e666967203d206374782e67657428226d617022290a20202020202020206167656e745f636f6e6669675b7265736f757263652e6167656e746e616d655d203d207265736f757263652e7572690a202020202020202073656c662e5f7365745f6d6170286167656e745f636f6e666967290a
7d6539a4d7ba19b65225673c0bc5d7601787ed2b	\\x2222220a436f70797269676874203230323420496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f7274206f730a0a696d706f727420696e6d616e74615f706c7567696e732e66732e7265736f7572636573202023206e6f71613a20463430310a66726f6d20696e6d616e74612e6d6f64756c6520696d706f72742050726f6a6563740a66726f6d20696e6d616e74612e706c7567696e7320696d706f727420436f6e746578742c20706c7567696e0a0a0a646566205f657874656e645f70617468286374783a20436f6e746578742c20706174683a20737472293a0a2020202063757272656e745f6d6f64756c655f707265666978203d20222e22202b206f732e706174682e7365700a20202020696620706174682e737461727473776974682863757272656e745f6d6f64756c655f707265666978293a0a20202020202020206d6f64756c655f616e645f7375626d6f64756c655f6e616d655f7061727473203d206374782e6f776e65722e6e616d6573706163652e6765745f66756c6c5f6e616d6528292e73706c6974280a202020202020202020202020223a3a220a2020202020202020290a20202020202020206d6f64756c655f6e616d65203d206d6f64756c655f616e645f7375626d6f64756c655f6e616d655f70617274735b305d0a20202020202020206966206d6f64756c655f6e616d6520696e2050726f6a6563742e67657428292e6d6f64756c65732e6b65797328293a0a20202020202020202020202072657475726e206f732e706174682e6a6f696e286d6f64756c655f6e616d652c20706174685b6c656e2863757272656e745f6d6f64756c655f70726566697829203a5d290a2020202020202020656c73653a0a202020202020202020202020726169736520457863657074696f6e280a202020202020202020202020202020206622556e61626c6520746f2064657465726d696e652063757272656e74206d6f64756c6520666f722070617468207b706174687d2c2063616c6c65642066726f6d207b6374782e6f776e65722e6e616d6573706163652e6765745f66756c6c5f6e616d6528297d220a202020202020202020202020290a2020202072657475726e20706174680a0a0a6465662064657465726d696e655f70617468286374783a20436f6e746578742c206d6f64756c655f6469723a207374722c20706174683a20737472293a0a202020202222220a2020202044657465726d696e6520746865207265616c2070617468206261736564206f6e2074686520676976656e20706174680a202020202222220a2020202070617468203d205f657874656e645f70617468286374782c2070617468290a202020207061727473203d20706174682e73706c6974286f732e706174682e736570290a0a202020206d6f64756c6573203d2050726f6a6563742e67657428292e6d6f64756c65730a0a2020202069662070617274735b305d203d3d2022223a0a20202020202020206d6f64756c655f70617468203d2050726f6a6563742e67657428292e70726f6a6563745f706174680a20202020656c69662070617274735b305d206e6f7420696e206d6f64756c65733a0a2020202020202020726169736520457863657074696f6e2866224d6f64756c65207b70617274735b305d7d20646f6573206e6f7420657869737420666f722070617468207b706174687d22290a20202020656c73653a0a20202020202020206d6f64756c655f70617468203d206d6f64756c65735b70617274735b305d5d2e5f706174680a0a2020202072657475726e206f732e706174682e6a6f696e286d6f64756c655f706174682c206d6f64756c655f6469722c206f732e706174682e7365702e6a6f696e2870617274735b313a5d29290a0a0a646566206765745f66696c655f636f6e74656e74286374783a20436f6e746578742c206d6f64756c655f6469723a207374722c20706174683a20737472293a0a202020202222220a202020204765742074686520636f6e74656e7473206f6620612066696c650a202020202222220a2020202066696c656e616d65203d2064657465726d696e655f70617468286374782c206d6f64756c655f6469722c2070617468290a0a2020202069662066696c656e616d65206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822257320646f6573206e6f742065786973742220252070617468290a0a202020206966206e6f74206f732e706174682e697366696c652866696c656e616d65293a0a2020202020202020726169736520457863657074696f6e2866227b706174687d2069736e277420612076616c69642066696c6520287b66696c656e616d657d2922290a0a2020202066696c655f6664203d206f70656e2866696c656e616d65290a2020202069662066696c655f6664206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822556e61626c6520746f206f70656e2066696c652025732220252066696c656e616d65290a0a20202020636f6e74656e74203d2066696c655f66642e7265616428290a2020202066696c655f66642e636c6f736528290a0a2020202072657475726e20636f6e74656e740a0a0a40706c7567696e0a64656620736f75726365286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e2022737472696e67223a20202320747970653a69676e6f72655b6e616d652d646566696e65645d0a202020202222220a2020202052657475726e20746865207465787475616c20636f6e74656e7473206f662074686520676976656e2066696c650a202020202222220a2020202072657475726e206765745f66696c655f636f6e74656e74286374782c202266696c6573222c2070617468290a0a0a636c6173732046696c654d61726b657228737472293a0a202020202222220a202020204d61726b657220636c61737320746f20696e6469636174652074686174207468697320737472696e672069732061637475616c6c792061207265666572656e636520746f20612066696c65206f6e206469736b2e0a0a2020202054686973206d656368616e69736d206973206261636b7761726420636f6d70617469626c65207769746820746865206f6c6420696e2d62616e64206d656368616e69736d2e0a0a20202020546f20706173732066696c65207265666572656e6365732066726f6d206f74686572206d6f64756c65732c20796f752063616e20636f7079207061737465207468697320636c61737320696e746f20796f7572206f776e206d6f64756c652e0a20202020546865206d61746368696e6720696e207468652066696c652068616e646c65722069733a0a0a20202020202020206966202246696c654d61726b65722220696e20636f6e74656e742e5f5f636c6173735f5f2e5f5f6e616d655f5f0a0a202020202222220a0a20202020646566205f5f6e65775f5f28636c732c2066696c656e616d65293a0a20202020202020206f626a203d207374722e5f5f6e65775f5f28636c732c2022696d702d6d6f64756c652d736f757263653a66696c653a2f2f22202b2066696c656e616d65290a20202020202020206f626a2e66696c656e616d65203d2066696c656e616d650a202020202020202072657475726e206f626a0a0a0a40706c7567696e0a6465662066696c65286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e2022737472696e67223a20202320747970653a69676e6f72655b6e616d652d646566696e65645d0a202020202222220a2020202052657475726e20746865207465787475616c20636f6e74656e7473206f662074686520676976656e2066696c650a202020202222220a2020202066696c656e616d65203d2064657465726d696e655f70617468286374782c202266696c6573222c2070617468290a0a2020202069662066696c656e616d65206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822257320646f6573206e6f742065786973742220252070617468290a0a202020206966206e6f74206f732e706174682e697366696c652866696c656e616d65293a0a2020202020202020726169736520457863657074696f6e282225732069736e277420612076616c69642066696c652220252066696c656e616d65290a0a2020202072657475726e2046696c654d61726b6572286f732e706174682e616273706174682866696c656e616d6529290a0a0a40706c7567696e0a646566206c6973745f66696c6573286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e20226c697374223a20202320747970653a69676e6f72655b6e616d652d646566696e65645d0a202020202222220a202020204c6973742066696c657320696e2061206469726563746f72790a202020202222220a2020202070617468203d2064657465726d696e655f70617468286374782c202266696c6573222c2070617468290a2020202072657475726e205b6620666f72206620696e206f732e6c697374646972287061746829206966206f732e706174682e697366696c65286f732e706174682e6a6f696e28706174682c206629295d0a
ca7f66803b24e0b831d6728f882f5a79af2f33c2	\\x2222220a436f70797269676874203230323420496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f727420636f70790a696d706f727420656e756d0a696d706f7274206a736f6e0a696d706f727420747970696e670a0a696d706f727420696e6d616e74615f706c7567696e732e6d69746f67656e2e6162630a696d706f727420696e6d616e74615f706c7567696e732e7374640a696d706f72742079616d6c0a0a696d706f727420696e6d616e74612e6167656e742e68616e646c65720a696d706f727420696e6d616e74612e636f6e73740a696d706f727420696e6d616e74612e657865637574652e70726f78790a696d706f727420696e6d616e74612e657865637574652e7574696c0a696d706f727420696e6d616e74612e6578706f72740a696d706f727420696e6d616e74612e706c7567696e730a696d706f727420696e6d616e74612e7265736f75726365730a66726f6d20696e6d616e74612e7574696c20696d706f727420646963745f706174680a0a0a636c617373204f7065726174696f6e287374722c20656e756d2e456e756d293a0a202020205245504c414345203d20227265706c616365220a2020202052454d4f5645203d202272656d6f7665220a202020204d45524745203d20226d65726765220a0a0a64656620757064617465280a20202020636f6e6669673a20646963742c20706174683a20646963745f706174682e44696374506174682c206f7065726174696f6e3a204f7065726174696f6e2c20646573697265643a206f626a6563740a29202d3e20646963743a0a202020202222220a202020205570646174652074686520636f6e66696720636f6e666967206174207468652073706563696669656420747970652c207573696e6720676976656e206f7065726174696f6e20616e6420646573697265642076616c75652e0a0a202020203a706172616d20636f6e6669673a2054686520636f6e66696775726174696f6e20746f207570646174650a202020203a706172616d20706174683a20546865207061746820706f696e74696e6720746f20616e20656c656d656e74206f662074686520636f6e66696720746861742073686f756c64206265206d6f6469666965640a202020203a706172616d206f7065726174696f6e3a205468652074797065206f66206f7065726174696f6e20746f206170706c7920746f2074686520636f6e66696720656c656d656e740a202020203a706172616d20646573697265643a20546865206465736972656420737461746520746f206170706c7920746f2074686520636f6e66696720656c656d656e740a202020202222220a202020206966206f7065726174696f6e203d3d204f7065726174696f6e2e52454d4f56453a0a2020202020202020706174682e72656d6f766528636f6e666967290a202020202020202072657475726e20636f6e6669670a0a202020206966206f7065726174696f6e203d3d204f7065726174696f6e2e5245504c4143453a0a2020202020202020706174682e7365745f656c656d656e7428636f6e6669672c2076616c75653d64657369726564290a202020202020202072657475726e20636f6e6669670a0a202020206966206f7065726174696f6e203d3d204f7065726174696f6e2e4d455247453a0a20202020202020206966206e6f74206973696e7374616e636528646573697265642c2064696374293a0a20202020202020202020202072616973652056616c75654572726f72280a2020202020202020202020202020202066224d65726765206f7065726174696f6e206973206f6e6c7920737570706f7274656420666f722064696374732c2062757420676f74207b747970652864657369726564297d20220a202020202020202020202020202020206622287b646573697265647d29220a202020202020202020202020290a202020202020202063757272656e74203d20706174682e6765745f656c656d656e7428636f6e6669672c20636f6e7374727563743d54727565290a20202020202020206966206e6f74206973696e7374616e63652863757272656e742c2064696374293a0a20202020202020202020202072616973652056616c75654572726f72280a2020202020202020202020202020202066224120646963742063616e206f6e6c79206d65206d657267656420746f206120646963742c2063757272656e742076616c75652061742070617468207b706174687d20220a2020202020202020202020202020202066226973206e6f74206120646963743a207b63757272656e747d20287b747970652863757272656e74297d29220a202020202020202020202020290a202020202020202063757272656e742e757064617465287b6b3a207620666f72206b2c207620696e20646573697265642e6974656d7328292069662076206973206e6f74204e6f6e657d290a202020202020202072657475726e20636f6e6669670a0a2020202072616973652056616c75654572726f72286622556e737570706f72746564206f7065726174696f6e3a207b6f7065726174696f6e7d22290a0a0a40696e6d616e74612e7265736f75726365732e7265736f75726365280a202020206e616d653d2266733a3a4a736f6e46696c65222c0a2020202069645f6174747269627574653d22757269222c0a202020206167656e743d22686f73742e6e616d65222c0a290a636c617373204a736f6e46696c655265736f7572636528696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e5265736f75726365414243293a0a202020206669656c6473203d20280a20202020202020202270617468222c0a2020202020202020227065726d697373696f6e73222c0a2020202020202020226f776e6572222c0a20202020202020202267726f7570222c0a202020202020202022757269222c0a202020202020202022696e64656e74222c0a202020202020202022666f726d6174222c0a20202020202020202276616c756573222c0a20202020290a20202020706174683a207374720a202020207065726d697373696f6e733a20696e74207c204e6f6e650a202020206f776e65723a20737472207c204e6f6e650a2020202067726f75703a20737472207c204e6f6e650a2020202076616c7565733a206c6973745b646963745d0a20202020666f726d61743a20747970696e672e4c69746572616c5b226a736f6e222c202279616d6c225d0a20202020696e64656e743a20696e740a0a2020202040636c6173736d6574686f640a20202020646566206765745f76616c75657328636c732c205f2c20656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f787929202d3e206c6973745b646963745d3a0a202020202020202072657475726e205b0a2020202020202020202020207b0a202020202020202020202020202020202270617468223a2076616c75652e706174682c0a20202020202020202020202020202020226f7065726174696f6e223a2076616c75652e6f7065726174696f6e2c0a202020202020202020202020202020202276616c7565223a2076616c75652e76616c75652c0a2020202020202020202020207d0a202020202020202020202020666f722076616c756520696e20656e746974792e76616c7565730a20202020202020205d0a0a2020202040636c6173736d6574686f640a20202020646566206765745f75726928636c732c205f2c20656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f787929202d3e207374723a0a20202020202020202222220a2020202020202020436f6d706f736520612075726920746f206964656e7469667920746865207265736f757263652c20616e6420776869636820616c6c6f7773206d756c7469706c65207265736f75726365730a2020202020202020746f206d616e616765207468652073616d652066696c652e0a20202020202020202222220a2020202020202020696620656e746974792e7265736f757263655f6469736372696d696e61746f723a0a20202020202020202020202072657475726e2066227b656e746974792e706174687d3a7b656e746974792e7265736f757263655f6469736372696d696e61746f727d220a202020202020202072657475726e20656e746974792e706174680a0a2020202040636c6173736d6574686f640a20202020646566206765745f7065726d697373696f6e73280a2020202020202020636c732c0a20202020202020205f3a20696e6d616e74612e6578706f72742e4578706f727465722c0a2020202020202020656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78792c0a2020202029202d3e20696e74207c204e6f6e653a0a202020202020202072657475726e20696e7428656e746974792e6d6f64652920696620656e746974792e6d6f6465206973206e6f74204e6f6e6520656c7365204e6f6e650a0a0a40696e6d616e74612e6167656e742e68616e646c65722e70726f7669646572282266733a3a4a736f6e46696c65222c202222290a636c617373204a736f6e46696c6548616e646c657228696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e48616e646c65724142435b4a736f6e46696c655265736f757263655d293a0a202020206465662066726f6d5f6a736f6e2873656c662c207261773a207374722c202a2c20666f726d61743a20747970696e672e4c69746572616c5b226a736f6e222c202279616d6c225d29202d3e206f626a6563743a0a20202020202020202222220a2020202020202020436f6e766572742061206a736f6e2d6c696b652072617720737472696e6720696e2074686520657870656374656420666f726d617420746f2074686520636f72726573706f6e64696e670a2020202020202020707974686f6e20646963742d6c696b65206f626a6563742e0a0a20202020202020203a706172616d207261773a20546865207261772076616c75652c206173207265616420696e207468652066696c652e0a20202020202020203a706172616d20666f726d61743a2054686520666f726d6174206f66207468652076616c75652e0a20202020202020202222220a2020202020202020696620666f726d6174203d3d20226a736f6e223a0a20202020202020202020202072657475726e206a736f6e2e6c6f61647328726177290a2020202020202020696620666f726d6174203d3d202279616d6c223a0a20202020202020202020202072657475726e2079616d6c2e736166655f6c6f616428726177290a202020202020202072616973652056616c75654572726f72286622556e737570706f7274656420666f726d61743a207b666f726d61747d22290a0a2020202064656620746f5f6a736f6e280a202020202020202073656c662c0a202020202020202076616c75653a206f626a6563742c0a20202020202020202a2c0a2020202020202020666f726d61743a20747970696e672e4c69746572616c5b226a736f6e222c202279616d6c225d2c0a2020202020202020696e64656e743a20747970696e672e4f7074696f6e616c5b696e745d203d204e6f6e652c0a2020202029202d3e207374723a0a20202020202020202222220a202020202020202044756d70206120646963742d6c696b652073747275637475726520696e746f2061206a736f6e2d6c696b6520737472696e672e202054686520737472696e672063616e0a2020202020202020626520696e20646966666572656e7420666f726d6174732c20646570656e64696e67206f6e207468652076616c7565207370656369666965642e0a0a20202020202020203a706172616d2076616c75653a2054686520646963742d6c696b652076616c75652c20746f206265207772697474656e20746f2066696c652e0a20202020202020203a706172616d20666f726d61743a2054686520666f726d6174206f66207468652076616c75652e0a20202020202020203a706172616d20696e64656e743a205768657468657220616e7920696e64656e746174696f6e2073686f756c64206265206170706c69656420746f207468650a20202020202020202020202076616c7565207772697474656e20746f2066696c652e0a20202020202020202222220a2020202020202020696620666f726d6174203d3d20226a736f6e223a0a20202020202020202020202072657475726e206a736f6e2e64756d70732876616c75652c20696e64656e743d696e64656e74290a2020202020202020696620666f726d6174203d3d202279616d6c223a0a20202020202020202020202072657475726e2079616d6c2e736166655f64756d702876616c75652c20696e64656e743d696e64656e74290a202020202020202072616973652056616c75654572726f72286622556e737570706f7274656420666f726d61743a207b666f726d61747d22290a0a2020202064656620726561645f7265736f75726365280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a20202020202020207265736f757263653a204a736f6e46696c655265736f757263652c0a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a202020202020202020202020726169736520696e6d616e74612e6167656e742e68616e646c65722e5265736f7572636550757267656428290a0a2020202020202020666f72206b65792c2076616c756520696e2073656c662e70726f78792e66696c655f73746174287265736f757263652e70617468292e6974656d7328293a0a20202020202020202020202069662067657461747472287265736f757263652c206b657929206973206e6f74204e6f6e653a0a2020202020202020202020202020202073657461747472287265736f757263652c206b65792c2076616c7565290a0a202020202020202023204c6f61642074686520636f6e74656e74206f6620746865206578697374696e672066696c650a20202020202020207261775f636f6e74656e74203d2073656c662e70726f78792e726561645f62696e617279287265736f757263652e70617468292e6465636f646528290a20202020202020206374782e6465627567282252656164696e67206578697374696e672066696c65222c207261775f636f6e74656e743d7261775f636f6e74656e74290a202020202020202063757272656e745f636f6e74656e74203d2073656c662e66726f6d5f6a736f6e287261775f636f6e74656e742c20666f726d61743d7265736f757263652e666f726d6174290a20202020202020206374782e736574282263757272656e745f636f6e74656e74222c2063757272656e745f636f6e74656e74290a0a202020206465662063616c63756c6174655f64696666280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a202020202020202063757272656e743a204a736f6e46696c655265736f757263652c0a2020202020202020646573697265643a204a736f6e46696c655265736f757263652c0a2020202029202d3e20646963745b7374722c20646963745b7374722c206f626a6563745d5d3a0a20202020202020202320466f722066696c65207065726d697373696f6e7320616e64206f776e6572736869702c2077652064656c656761746520746f2074686520706172656e7420636c6173730a20202020202020206368616e676573203d20737570657228292e63616c63756c6174655f64696666286374782c2063757272656e742c2064657369726564290a0a20202020202020202320546f20636865636b20696620736f6d65206368616e676520636f6e74656e74206e6565647320746f206265206170706c6965642c20776520706572666f726d20612022737461626c6522206164646974696f6e0a202020202020202023206f7065726174696f6e3a205765206170706c79206f7572206465736972656420737461746520746f207468652063757272656e742073746174652c20616e6420636865636b2069662077652063616e207468656e0a2020202020202020232073656520616e7920646966666572656e63652e0a202020202020202063757272656e745f636f6e74656e74203d206374782e676574282263757272656e745f636f6e74656e7422290a2020202020202020646573697265645f636f6e74656e74203d20636f70792e64656570636f70792863757272656e745f636f6e74656e74290a2020202020202020666f722076616c756520696e20646573697265642e76616c7565733a0a202020202020202020202020757064617465280a20202020202020202020202020202020646573697265645f636f6e74656e742c0a20202020202020202020202020202020646963745f706174682e746f5f706174682876616c75655b2270617468225d292c0a202020202020202020202020202020204f7065726174696f6e2876616c75655b226f7065726174696f6e225d292c0a2020202020202020202020202020202076616c75655b2276616c7565225d2c0a202020202020202020202020290a0a202020202020202069662063757272656e745f636f6e74656e7420213d20646573697265645f636f6e74656e743a0a2020202020202020202020206368616e6765735b22636f6e74656e74225d203d207b0a202020202020202020202020202020202263757272656e74223a2063757272656e745f636f6e74656e742c0a202020202020202020202020202020202264657369726564223a20646573697265645f636f6e74656e742c0a2020202020202020202020207d0a0a202020202020202072657475726e206368616e6765730a0a20202020646566206372656174655f7265736f75726365280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a20202020202020207265736f757263653a204a736f6e46696c655265736f757263652c0a2020202029202d3e204e6f6e653a0a202020202020202023204275696c64206120636f6e666967206261736564206f6e20616c6c2074686520656c656d656e74732077652077616e7420746f206d616e6167650a2020202020202020636f6e74656e74203d207b7d0a2020202020202020666f722076616c756520696e207265736f757263652e76616c7565733a0a202020202020202020202020757064617465280a20202020202020202020202020202020636f6e74656e742c0a20202020202020202020202020202020646963745f706174682e746f5f706174682876616c75655b2270617468225d292c0a202020202020202020202020202020204f7065726174696f6e2876616c75655b226f7065726174696f6e225d292c0a2020202020202020202020202020202076616c75655b2276616c7565225d2c0a202020202020202020202020290a0a2020202020202020696e64656e74203d207265736f757263652e696e64656e74206966207265736f757263652e696e64656e7420213d203020656c7365204e6f6e650a20202020202020207261775f636f6e74656e74203d2073656c662e746f5f6a736f6e280a202020202020202020202020636f6e74656e742c0a202020202020202020202020666f726d61743d7265736f757263652e666f726d61742c0a202020202020202020202020696e64656e743d696e64656e742c0a2020202020202020290a202020202020202073656c662e70726f78792e707574287265736f757263652e706174682c207261775f636f6e74656e742e656e636f64652829290a0a20202020202020206966207265736f757263652e7065726d697373696f6e73206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a20202020202020206966207265736f757263652e6f776e6572206973206e6f74204e6f6e65206f72207265736f757263652e67726f7570206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f6372656174656428290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a20202020202020206368616e6765733a20646963745b7374722c20646963745b7374722c206f626a6563745d5d2c0a20202020202020207265736f757263653a204a736f6e46696c655265736f757263652c0a2020202029202d3e204e6f6e653a0a202020202020202069662022636f6e74656e742220696e206368616e6765733a0a202020202020202020202020636f6e74656e74203d206368616e6765735b22636f6e74656e74225d5b2264657369726564225d0a202020202020202020202020696e64656e74203d207265736f757263652e696e64656e74206966207265736f757263652e696e64656e7420213d203020656c7365204e6f6e650a2020202020202020202020207261775f636f6e74656e74203d2073656c662e746f5f6a736f6e280a20202020202020202020202020202020636f6e74656e742c0a20202020202020202020202020202020666f726d61743d7265736f757263652e666f726d61742c0a20202020202020202020202020202020696e64656e743d696e64656e742c0a202020202020202020202020290a20202020202020202020202073656c662e70726f78792e707574287265736f757263652e706174682c207261775f636f6e74656e742e656e636f64652829290a0a2020202020202020696620226d6f64652220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a2020202020202020696620226f776e65722220696e206368616e676573206f72202267726f75702220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f7570646174656428290a0a202020206465662064656c6574655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a204a736f6e46696c655265736f757263650a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e72656d6f7665287265736f757263652e70617468290a20202020202020206374782e7365745f70757267656428290a
4ac629bdc461bf185971b82b4fc3dd457fba3fdd	\\x2222220a436f70797269676874203230323320496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f727420707964616e7469630a0a0a6465662072656765785f737472696e672872656765783a2073747229202d3e20747970653a0a202020202222220a202020204275696c64206120726567657820636f6e73747261696e656420737472696e67207468617420697320626f746820737570706f7274656420627920707964616e74696320763120616e642076320a0a202020203a706172616d2072656765783a204120726567657820737472696e670a202020203a72657475726e3a204120747970652074686174207468652063757272656e7420707964616e7469632063616e2075736520666f722076616c69646174696f6e0a202020202222220a202020207472793a0a202020202020202066726f6d20696e6d616e74612e76616c69646174696f6e5f7479706520696d706f72742072656765785f737472696e6720617320636f72655f72656765785f737472696e670a2020202065786365707420496d706f72744572726f723a0a2020202020202020232076312028616c6c2076657273696f6e73206f6620636f726520746861742075736520763220686176652074686973206d6574686f64290a202020202020202072657475726e20707964616e7469632e636f6e7374722872656765783d7265676578290a20202020656c73653a0a2020202020202020232064656c656761746520746f20636f72650a202020202020202072657475726e20636f72655f72656765785f737472696e67287265676578290a
30b3be6c2af081c7ea8594e5424428222d3c1cba	\\x2222220a436f70797269676874203230313620496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f7274206261736536340a696d706f7274206275696c74696e730a696d706f727420686173686c69620a696d706f727420696d706f72746c69620a696d706f7274206970616464726573730a696d706f7274206a736f6e0a696d706f7274206c6f6767696e670a696d706f7274206f730a696d706f72742072616e646f6d0a696d706f72742072650a696d706f72742074696d650a696d706f727420747970696e670a66726f6d20636f6c6c656374696f6e7320696d706f72742064656661756c74646963740a66726f6d20636f6c6c656374696f6e732e61626320696d706f7274204974657261746f722c2053657175656e63650a66726f6d2069746572746f6f6c7320696d706f727420636861696e0a66726f6d206f70657261746f7220696d706f727420617474726765747465720a66726f6d20747970696e6720696d706f727420416e792c204f7074696f6e616c2c205475706c650a0a696d706f7274206a696e6a61320a696d706f727420707964616e7469630a66726f6d206a696e6a613220696d706f727420456e7669726f6e6d656e742c2046696c6553797374656d4c6f616465722c205072656669784c6f616465722c2054656d706c6174650a66726f6d206a696e6a61322e657863657074696f6e7320696d706f727420556e646566696e65644572726f720a66726f6d206a696e6a61322e72756e74696d6520696d706f727420556e646566696e65642c206d697373696e670a0a2320646f6e27742062696e6420746f20607265736f75726365736020626563617573652074686973207061636b616765206861732061207375626d6f64756c65206e616d6564207265736f757263657320746861742077696c6c2062696e6420746f20607265736f757263657360207768656e20696d706f727465640a696d706f727420696e6d616e74612e7265736f75726365730a66726f6d20696e6d616e746120696d706f7274207574696c0a66726f6d20696e6d616e74612e6167656e742e68616e646c657220696d706f7274204c6f676765724142430a66726f6d20696e6d616e74612e61737420696d706f7274204e6f74466f756e64457863657074696f6e2c204f7074696f6e616c56616c7565457863657074696f6e2c2052756e74696d65457863657074696f6e0a66726f6d20696e6d616e74612e636f6e66696720696d706f727420436f6e6669670a66726f6d20696e6d616e74612e6578656375746520696d706f72742070726f78790a66726f6d20696e6d616e74612e657865637574652e7574696c20696d706f7274204e6f6e6556616c75652c20556e6b6e6f776e0a66726f6d20696e6d616e74612e6578706f727420696d706f727420646570656e64656e63795f6d616e616765722c20756e6b6e6f776e5f706172616d65746572730a66726f6d20696e6d616e74612e6d6f64756c6520696d706f72742050726f6a6563740a66726f6d20696e6d616e74612e706c7567696e7320696d706f727420436f6e746578742c20506c7567696e457863657074696f6e2c20646570726563617465642c20706c7567696e0a66726f6d20696e6d616e74612e70726f746f636f6c20696d706f727420656e64706f696e74730a0a737570706f7274735f70726f78795f636f6e746578743a20626f6f6c0a7472793a0a2020202066726f6d20696e6d616e74612e657865637574652e70726f787920696d706f72742050726f7879436f6e746578740a2020202066726f6d20696e6d616e74612e706c7567696e7320696d706f727420616c6c6f775f7265666572656e63655f76616c7565730a0a20202020737570706f7274735f70726f78795f636f6e74657874203d20547275650a65786365707420496d706f72744572726f723a0a20202020737570706f7274735f70726f78795f636f6e74657874203d2046616c73650a0a2020202023206f6c64657220696e6d616e74612d636f72652076657273696f6e7320283c31362920646f6e277420737570706f7274207468697320796574203d3e206d6f636b20697420746f2072657475726e204e6f6e650a202020206465662050726f7879436f6e74657874282a2a6b77617267733a206f626a65637429202d3e204e6f6e653a20202320747970653a2069676e6f72650a202020202020202072657475726e204e6f6e650a0a2020202064656620616c6c6f775f7265666572656e63655f76616c7565735b545d28696e7374616e63653a205429202d3e20543a0a202020202020202072657475726e20696e7374616e63650a0a0a636c617373204d6f636b5265666572656e63653a0a202020202222220a202020205265666572656e6365206261636b776172647320636f6d7061746962696c697479206f626a65637420666f722075736520696e20706c7567696e207479706520616e6e6f746174696f6e732e205768656e20616e6e6f74617465642c206163747320617320616e20616c69617320666f720a20202020606f626a656374602e0a202020202222220a0a20202020646566205f5f636c6173735f6765746974656d5f5f2873656c662c206b65793a2073747229202d3e206275696c74696e732e747970655b6f626a6563745d3a0a202020202020202072657475726e206f626a6563740a0a0a7472793a0a2020202066726f6d20696e6d616e74612e7265666572656e63657320696d706f7274205265666572656e63650a65786365707420496d706f72744572726f723a0a202020205265666572656e6365203d204d6f636b5265666572656e636520202320747970653a2069676e6f72650a0a0a40706c7567696e0a64656620756e697175655f66696c65280a202020207072656669783a2022737472696e67222c20736565643a2022737472696e67222c207375666669783a2022737472696e67222c206c656e6774683a2022696e7422203d2032300a29202d3e2022737472696e67223a0a2020202072657475726e20707265666978202b20686173686c69622e6d643528736565642e656e636f646528227574662d382229292e6865786469676573742829202b207375666669780a0a0a7463616368653a20646963745b7374722c2054656d706c6174655d203d207b7d0a0a656e67696e655f6361636865203d204e6f6e650a0a0a64656620696e6d616e74615f72657365745f73746174652829202d3e204e6f6e653a0a202020202222220a20202020526573657420746865207374617465206b6570742062792074686973206d6f64756c652e0a202020202222220a20202020676c6f62616c207463616368652c20656e67696e655f63616368652c20666163745f63616368650a20202020746361636865203d207b7d0a20202020656e67696e655f6361636865203d204e6f6e650a20202020666163745f6361636865203d207b7d0a0a0a636c617373204a696e6a6144796e616d696350726f78795b503a2070726f78792e44796e616d696350726f78795d2870726f78792e44796e616d696350726f7879293a0a202020202222220a2020202044796e616d69632070726f7879206275696c74206f6e20746f70206f6620696e6d616e74612d636f726527732044796e616d696350726f787920746f2070726f76696465204a696e6a612d7370656369666963206361706162696c69746965732e0a202020202222220a0a20202020646566205f5f696e69745f5f2873656c662c20696e7374616e63653a205029202d3e204e6f6e653a0a20202020202020206966206861736174747228696e7374616e63652c20225f6765745f636f6e7465787422293a0a202020202020202020202020737570657228292e5f5f696e69745f5f28696e7374616e63652e5f6765745f696e7374616e636528292c20636f6e746578743d696e7374616e63652e5f6765745f636f6e746578742829290a2020202020202020656c73653a0a20202020202020202020202023206261636b776172647320636f6d7061746962696c69747920666f72206f6c64657220696e6d616e74612d636f72652076657273696f6e7320283c3136290a202020202020202020202020737570657228292e5f5f696e69745f5f28696e7374616e63652e5f6765745f696e7374616e63652829290a20202020202020206f626a6563742e5f5f736574617474725f5f2873656c662c20225f5f64656c6567617465222c20696e7374616e6365290a0a20202020646566205f6765745f64656c65676174652873656c6629202d3e20503a0a20202020202020202222220a202020202020202047657420746865206e6f726d616c2070726f7879206f626a656374206261636b696e672074686973206f6e652e0a20202020202020202222220a202020202020202072657475726e206f626a6563742e5f5f6765746174747269627574655f5f2873656c662c20225f5f64656c656761746522290a0a2020202040636c6173736d6574686f640a202020206465662072657475726e5f76616c7565280a2020202020202020636c732c0a202020202020202076616c75653a206f626a6563742c0a20202020202020202a2c0a2020202020202020636f6e746578743a204f7074696f6e616c5b2270726f78792e50726f7879436f6e74657874225d203d204e6f6e652c0a2020202029202d3e206f626a6563743a0a20202020202020202222220a2020202020202020436f6e766572747320612076616c75652066726f6d2074686520696e7465726e616c20646f6d61696e20746f20746865204a696e6a6120646f6d61696e2e0a0a2020202020202020436f726527732044796e616d696350726f787920696d706c656d656e746174696f6e2077696c6c206e6f742063616c6c2074686973206d6574686f642c206576656e20666f7220737562636c6173736573206f662074686973206f6e652e204974206973206d65616e7420707572656c7920617320610a2020202020202020636f6e76656e69656e6365206d6574686f6420746f702d6c6576656c20636f6e76657273696f6e2e0a0a20202020202020203a706172616d20636f6e746578743a205468652070726f787920636f6e746578742e20416c6c6f77656420746f206265204e6f6e6520666f72206261636b776172647320636f6d7061746962696c6974792c20696e2077686963682063617365206572726f72207265706f7274696e672077696c6c0a2020202020202020202020206265206c6573732061636375726174652e0a20202020202020202222220a20202020202020206966206e6f7420737570706f7274735f70726f78795f636f6e746578743a0a20202020202020202020202023206261636b776172647320636f6d7061746962696c6974792077697468206f6c64657220696e6d616e74612d636f726520283c3136290a20202020202020202020202072657475726e20636c732e7772617028737570657228292e72657475726e5f76616c75652876616c756529290a0a2020202020202020636f6e74657874203d20280a202020202020202020202020636f6e746578740a202020202020202020202020696620636f6e74657874206973206e6f74204e6f6e650a202020202020202020202020656c73652070726f78792e50726f7879436f6e7465787428706174683d6f626a6563742e5f5f726570725f5f2876616c7565292c2076616c6964617465643d46616c7365290a2020202020202020290a0a20202020202020202320636f6e746578742077617320696e74726f6475636564206166746572207265666572656e6365730a2020202020202020617373657274205265666572656e6365206973206e6f74204d6f636b5265666572656e636520202320747970653a2069676e6f72650a20202020202020202320636f726527732044796e616d696350726f78792074616b65732063617265206f66207265666572656e636573206f6e2d70726f78792e20427574207765206861766520746f20677561726420746f702d6c6576656c207265666572656e636573206865726520626563617573650a202020202020202023207468657920617265206e657665722072656a65637465642061742072756e74696d65206f6e2074686520706c7567696e20626f756e646172792028636f72652773206e6f726d616c206f7065726174696e67206d6f6465292e0a20202020202020206966206973696e7374616e63652876616c75652c205265666572656e6365293a0a202020202020202020202020726169736520506c7567696e457863657074696f6e280a202020202020202020202020202020206622456e636f756e7465726564207265666572656e636520696e204a696e6a612074656d706c61746520666f72207661726961626c65207b636f6e746578742e706174687d20283d20607b76616c756521727d6029220a202020202020202020202020290a0a202020202020202072657475726e20636c732e7772617028737570657228292e72657475726e5f76616c75652876616c75652c20636f6e746578743d636f6e7465787429290a0a20202020646566205f72657475726e5f76616c75652873656c662c2076616c75653a206f626a6563742c202a2c2072656c61746976655f706174683a2073747229202d3e206f626a6563743a0a202020202020202064656c65676174653a2070726f78792e44796e616d696350726f7879203d2073656c662e5f6765745f64656c656761746528290a2020202020202020696620686173617474722864656c65676174652c20225f72657475726e5f76616c756522293a0a20202020202020202020202072657475726e2073656c662e777261702864656c65676174652e5f72657475726e5f76616c75652876616c75652c2072656c61746976655f706174683d72656c61746976655f7061746829290a2020202020202020656c73653a0a20202020202020202020202072657475726e204a696e6a6144796e616d696350726f78792e72657475726e5f76616c75652876616c75652c20636f6e746578743d4e6f6e65290a0a2020202040636c6173736d6574686f640a20202020646566207772617028636c732c2076616c75653a206f626a65637429202d3e206f626a6563743a0a20202020202020202222220a20202020202020205772617020612076616c756520696e2061206a696e6a612d636f6d70617469626c652070726f78792c2069662072657175697265642e0a20202020202020202222220a202020202020202072657475726e20280a202020202020202020202020636c732e5f777261705f70726f78792876616c756529206966206973696e7374616e63652876616c75652c2070726f78792e44796e616d696350726f78792920656c73652076616c75650a2020202020202020290a0a2020202040636c6173736d6574686f640a20202020646566205f777261705f70726f787928636c732c2076616c75653a2070726f78792e44796e616d696350726f787929202d3e20224a696e6a6144796e616d696350726f7879223a0a20202020202020202222220a2020202020202020577261702061206e6f726d616c2070726f787920696e2061206a696e6a612d636f6d70617469626c65206f6e652e0a20202020202020202222220a20202020202020206d617463682076616c75653a0a20202020202020202020202063617365204a696e6a6144796e616d696350726f787928293a0a2020202020202020202020202020202072657475726e2076616c75650a202020202020202020202020636173652070726f78792e53657175656e636550726f787928293a0a2020202020202020202020202020202072657475726e204a696e6a6153657175656e636550726f78792876616c7565290a202020202020202020202020636173652070726f78792e4469637450726f787928293a0a2020202020202020202020202020202072657475726e204a696e6a614469637450726f78792876616c7565290a202020202020202020202020636173652070726f78792e4974657261746f7250726f787928293a0a2020202020202020202020202020202072657475726e204a696e6a614974657261746f7250726f78792876616c7565290a202020202020202020202020636173652070726f78792e43616c6c50726f787928293a0a2020202020202020202020202020202072657475726e204a696e6a6143616c6c50726f78792876616c7565290a202020202020202020202020636173652070726f78792e44796e616d696350726f787928293a0a2020202020202020202020202020202072657475726e204a696e6a6144796e616d696350726f78792876616c7565290a20202020202020202020202063617365205f6e657665723a0a20202020202020202020202020202020747970696e672e6173736572745f6e65766572285f6e65766572290a0a20202020646566205f5f676574617474725f5f2873656c662c206e616d653a2073747229202d3e206f626a6563743a0a2020202020202020696e7374616e6365203d2073656c662e5f6765745f696e7374616e636528290a20202020202020206966206861736174747228696e7374616e63652c20226765745f61747472696275746522293a0a2020202020202020202020207472793a0a2020202020202020202020202020202072657475726e2073656c662e7772617028676574617474722873656c662e5f6765745f64656c656761746528292c206e616d6529290a20202020202020202020202065786365707420284f7074696f6e616c56616c7565457863657074696f6e2c204e6f74466f756e64457863657074696f6e293a0a2020202020202020202020202020202072657475726e20556e646566696e6564280a2020202020202020202020202020202020202020227661726961626c65202573206e6f7420736574206f6e20257322202520286e616d652c20696e7374616e6365292c0a2020202020202020202020202020202020202020696e7374616e63652c0a20202020202020202020202020202020202020206e616d652c0a20202020202020202020202020202020290a2020202020202020656c73653a0a202020202020202020202020232041206e617469766520707974686f6e206f626a6563742e204e6f7420737570706f7274656420627920636f726527732044796e616d696350726f78790a20202020202020202020202072657475726e2073656c662e5f72657475726e5f76616c7565286765746174747228696e7374616e63652c206e616d65292c2072656c61746976655f706174683d66222e7b6e616d657d22290a0a0a636c617373204a696e6a614974657261746f7250726f7879284a696e6a6144796e616d696350726f78795b70726f78792e4974657261746f7250726f78795d293a0a202020202222220a202020204a696e6a612d636f6d70617469626c65206974657261746f722070726f78792e0a202020202222220a0a20202020646566205f69735f73657175656e63652873656c6629202d3e20626f6f6c3a0a202020202020202072657475726e2073656c662e5f6765745f64656c656761746528292e5f69735f73657175656e636528290a0a20202020646566205f5f697465725f5f2873656c6629202d3e204974657261746f725b6f626a6563745d3a0a202020202020202072657475726e2073656c660a0a20202020646566205f5f6e6578745f5f2873656c6629202d3e206f626a6563743a0a202020202020202072657475726e2073656c662e77726170286e6578742873656c662e5f6765745f64656c6567617465282929290a0a0a636c617373204a696e6a614765744974656d50726f78795b4b3a20696e74207c207374722c20503a2070726f78792e53657175656e636550726f7879207c2070726f78792e4469637450726f78795d280a202020204a696e6a6144796e616d696350726f78795b505d0a293a0a202020202222220a202020204a696e6a612d636f6d70617469626c652070726f787920666f72205f5f6765746974656d5f5f2028414243292e0a202020202222220a0a20202020646566205f5f6765746974656d5f5f2873656c662c206b65793a204b29202d3e206f626a6563743a0a202020202020202072657475726e2073656c662e777261702873656c662e5f6765745f64656c656761746528295b6b65795d290a0a20202020646566205f5f697465725f5f2873656c6629202d3e206f626a6563743a0a202020202020202072657475726e2073656c662e7772617028697465722873656c662e5f6765745f64656c6567617465282929290a0a20202020646566205f5f6c656e5f5f2873656c6629202d3e20696e743a0a202020202020202072657475726e206c656e2873656c662e5f6765745f64656c65676174652829290a0a0a636c617373204a696e6a6153657175656e636550726f7879284a696e6a614765744974656d50726f78795b696e742c2070726f78792e53657175656e636550726f78795d293a0a202020202222220a202020204a696e6a612d636f6d70617469626c652073657175656e63652070726f78792e0a202020202222220a0a0a636c617373204a696e6a614469637450726f7879284a696e6a614765744974656d50726f78795b7374722c2070726f78792e4469637450726f78795d293a0a202020202222220a202020204a696e6a612d636f6d70617469626c6520646963742070726f78792e0a202020202222220a0a0a636c617373204a696e6a6143616c6c50726f7879284a696e6a6144796e616d696350726f78795b70726f78792e43616c6c50726f78795d293a0a202020202222220a202020204a696e6a612d636f6d70617469626c652063616c6c61626c652070726f78792e0a202020202222220a0a20202020646566205f5f63616c6c5f5f2873656c662c202a617267733a206f626a6563742c202a2a6b77617267733a206f626a656374293a0a20202020202020202320696e6d616e74612d636f726527732043616c6c50726f787920646f6573206e6f742063616c6c2072657475726e5f76616c7565203d3e2063616c6c20697420686572650a202020202020202072657475726e2073656c662e5f72657475726e5f76616c7565280a20202020202020202020202073656c662e5f6765745f64656c65676174652829282a617267732c202a2a6b7761726773292c2072656c61746976655f706174683d22282e2e2e29220a2020202020202020290a0a0a636c617373205265736f6c766572436f6e74657874286a696e6a61322e72756e74696d652e436f6e74657874293a0a20202020646566207265736f6c76655f6f725f6d697373696e672873656c662c206b65793a2073747229202d3e20416e793a0a20202020202020207265736f6c766572203d2073656c662e706172656e745b227b7b7265736f6c766572225d0a20202020202020207472793a0a202020202020202020202020726177203d207265736f6c7665722e6c6f6f6b7570286b6579290a20202020202020202020202072657475726e204a696e6a6144796e616d696350726f78792e72657475726e5f76616c7565280a202020202020202020202020202020207261772e6765745f76616c756528292c20636f6e746578743d50726f7879436f6e7465787428706174683d6b65792c2076616c6964617465643d46616c7365290a202020202020202020202020290a2020202020202020657863657074204e6f74466f756e64457863657074696f6e3a0a20202020202020202020202072657475726e207375706572285265736f6c766572436f6e746578742c2073656c66292e7265736f6c76655f6f725f6d697373696e67286b6579290a2020202020202020657863657074204f7074696f6e616c56616c7565457863657074696f6e3a0a20202020202020202020202072657475726e206d697373696e670a0a0a636c61737320456d7074795265736f6c7665723a0a202020202222220a20202020456d707479207265736f6c7665722c206d61746368696e6720746865206170692074686174205265736f6c766572436f6e746578742e7265736f6c76655f6f725f6d697373696e670a20202020657870656374732e2020416c77617973207261697365732061204e6f74466f756e64457863657074696f6e207768656e206c6f6f6b75702069732063616c6c65642e0a0a2020202054686973207265736f6c7665722069732075736564207768656e20746865207661726961626c652061636365737369626c6520746f207468652074656d706c617465206172650a2020202070726f76696465642076696120617267756d656e7473206f662074686520706c7567696e20696e7374656164206f66206c6f63616c207661726961626c657320696e207468650a202020206d6f64656c2e0a202020202222220a0a20202020646566206c6f6f6b75702873656c662c206b65793a2073747229202d3e207374723a0a20202020202020207261697365204e6f74466f756e64457863657074696f6e284e6f6e652c206b6579290a0a0a646566205f6765745f74656d706c6174655f656e67696e65286374783a20436f6e7465787429202d3e20456e7669726f6e6d656e743a0a202020202222220a20202020496e697469616c697a65207468652074656d706c61746520656e67696e6520656e7669726f6e6d656e740a202020202222220a20202020676c6f62616c20656e67696e655f63616368650a20202020696620656e67696e655f6361636865206973206e6f74204e6f6e653a0a202020202020202072657475726e20656e67696e655f63616368650a0a202020206c6f616465725f6d6170203d207b7d0a202020206c6f616465725f6d61705b22225d203d2046696c6553797374656d4c6f61646572280a20202020202020206f732e706174682e6a6f696e2850726f6a6563742e67657428292e70726f6a6563745f706174682c202274656d706c6174657322290a20202020290a20202020666f72206e616d652c206d6f64756c6520696e2050726f6a6563742e67657428292e6d6f64756c65732e6974656d7328293a0a202020202020202074656d706c6174655f646972203d206f732e706174682e6a6f696e286d6f64756c652e5f706174682c202274656d706c6174657322290a20202020202020206966206f732e706174682e69736469722874656d706c6174655f646972293a0a2020202020202020202020206c6f616465725f6d61705b6e616d655d203d2046696c6553797374656d4c6f616465722874656d706c6174655f646972290a0a202020202320696e69742074686520656e7669726f6e6d656e740a20202020656e76203d20456e7669726f6e6d656e74286c6f616465723d5072656669784c6f61646572286c6f616465725f6d6170292c20756e646566696e65643d6a696e6a61322e537472696374556e646566696e6564290a20202020656e762e636f6e746578745f636c617373203d205265736f6c766572436f6e746578740a0a202020202320726567697374657220616c6c20706c7567696e732061732066696c746572730a20202020666f72206e616d652c20636c7320696e206374782e6765745f636f6d70696c657228292e6765745f706c7567696e7328292e6974656d7328293a0a0a2020202020202020646566206375727977726170706572286e616d653a207374722c2066756e63293a0a202020202020202020202020646566207361666577726170706572282a61726773293a0a202020202020202020202020202020205f72616973655f69665f636f6e7461696e735f756e646566696e65642861726773290a2020202020202020202020202020202072657475726e204a696e6a6144796e616d696350726f78792e72657475726e5f76616c7565280a202020202020202020202020202020202020202066756e63282a61726773292c20636f6e746578743d50726f7879436f6e7465787428706174683d6e616d652c2076616c6964617465643d46616c7365290a20202020202020202020202020202020290a0a20202020202020202020202072657475726e2073616665777261707065720a0a20202020202020206a696e6a615f6e616d653a20737472203d206e616d652e7265706c61636528223a3a222c20222e22290a2020202020202020656e762e66696c746572735b6a696e6a615f6e616d655d203d206375727977726170706572286a696e6a615f6e616d652c20636c73290a0a20202020656e67696e655f6361636865203d20656e760a2020202072657475726e20656e760a0a0a646566205f72616973655f69665f636f6e7461696e735f756e646566696e656428617267733a205475706c655b6f626a6563742c202e2e2e5d29202d3e204e6f6e653a0a20202020756e6465665f61726773203d205b61726720666f722061726720696e2061726773206966206973696e7374616e6365286172672c206a696e6a61322e537472696374556e646566696e6564295d0a20202020696620756e6465665f617267733a0a20202020202020202320416363657373696e6720616e20756e646566696e65642076616c75652077696c6c2072616973652074686520617070726f70726961746520556e646566696e65644572726f720a202020202020202073747228756e6465665f617267735b305d290a0a0a646566205f657874656e645f70617468286374783a20436f6e746578742c20706174683a20737472293a0a2020202063757272656e745f6d6f64756c655f707265666978203d20222e22202b206f732e706174682e7365700a20202020696620706174682e737461727473776974682863757272656e745f6d6f64756c655f707265666978293a0a20202020202020206d6f64756c655f616e645f7375626d6f64756c655f6e616d655f7061727473203d206374782e6f776e65722e6e616d6573706163652e6765745f66756c6c5f6e616d6528292e73706c6974280a202020202020202020202020223a3a220a2020202020202020290a20202020202020206d6f64756c655f6e616d65203d206d6f64756c655f616e645f7375626d6f64756c655f6e616d655f70617274735b305d0a20202020202020206966206d6f64756c655f6e616d6520696e2050726f6a6563742e67657428292e6d6f64756c65732e6b65797328293a0a20202020202020202020202072657475726e206f732e706174682e6a6f696e286d6f64756c655f6e616d652c20706174685b6c656e2863757272656e745f6d6f64756c655f70726566697829203a5d290a2020202020202020656c73653a0a202020202020202020202020726169736520457863657074696f6e280a202020202020202020202020202020206622556e61626c6520746f2064657465726d696e652063757272656e74206d6f64756c6520666f722070617468207b706174687d2c2063616c6c65642066726f6d207b6374782e6f776e65722e6e616d6573706163652e6765745f66756c6c5f6e616d6528297d220a202020202020202020202020290a2020202072657475726e20706174680a0a0a40706c7567696e282274656d706c61746522290a6465662074656d706c617465286374783a20436f6e746578742c20706174683a2022737472696e67222c202a2a6b77617267733a2022616e792229202d3e2022737472696e67223a0a202020202222220a2020202045786563757465207468652074656d706c61746520696e207061746820696e207468652063757272656e7420636f6e746578742e20546869732066756e6374696f6e2077696c6c0a2020202067656e65726174652061206e65772073746174656d656e7420746861742068617320646570656e64656e63696573206f6e207468652075736564207661726961626c65732e0a0a202020203a706172616d20706174683a20546865207061746820746f20746865206a696e6a61322074656d706c61746520746861742073686f756c64206265207265736f6c7665642e0a202020203a706172616d202a2a6b77617267733a204120736574206f66207661726961626c657320746861742073686f756c64206f76657277726974652074686520636f6e746578740a202020202020202061636365737369626c6520746f207468652074656d706c6174652e0a202020202222220a202020206a696e6a615f656e76203d205f6765745f74656d706c6174655f656e67696e6528637478290a2020202074656d706c6174655f70617468203d205f657874656e645f70617468286374782c2070617468290a2020202069662074656d706c6174655f7061746820696e207463616368653a0a202020202020202074656d706c617465203d207463616368655b74656d706c6174655f706174685d0a20202020656c73653a0a202020202020202074656d706c617465203d206a696e6a615f656e762e6765745f74656d706c6174652874656d706c6174655f70617468290a20202020202020207463616368655b74656d706c6174655f706174685d203d2074656d706c6174650a0a202020206966206e6f74206b77617267733a0a202020202020202023204e6f206164646974696f6e616c206b7761726773206172652070726f76696465642c20757365207468652063757272656e7420636f6e746578740a20202020202020202320746f207265736f6c7665207468652074656d706c617465207661726961626c65730a20202020202020207661726961626c6573203d207b227b7b7265736f6c766572223a206374782e6765745f7265736f6c76657228297d0a20202020656c73653a0a20202020202020202320412073747269637420736574206f66207661726961626c65732069732070726f766964656420766961206b77617267732c206f6e6c79207573650a202020202020202023207468657365206173207661726961626c657320696e207468652074656d706c6174650a20202020202020207661726961626c6573203d2064696374286b7761726773290a20202020202020207661726961626c65735b227b7b7265736f6c766572225d203d20456d7074795265736f6c76657228290a0a202020207472793a0a202020202020202072657475726e2074656d706c6174652e72656e646572287661726961626c6573290a2020202065786365707420556e646566696e65644572726f7220617320653a0a20202020202020207261697365204e6f74466f756e64457863657074696f6e286374782e6f776e65722c204e6f6e652c20652e6d657373616765290a0a0a40646570656e64656e63795f6d616e616765720a646566206469725f6265666f72655f66696c65286d6f64656c2c207265736f7572636573293a0a202020202222220a20202020496620612066696c6520697320646566696e6564206f6e206120686f73742c207468656e206d616b65207468652066696c6520646570656e64206f6e2069747320706172656e74206469726563746f72790a202020202222220a2020202023206c6f6f70206f76657220616c6c207265736f757263657320746f2066696e642066696c657320616e6420646972730a202020207065725f686f7374203d2064656661756c7464696374286c697374290a202020207065725f686f73745f64697273203d2064656661756c7464696374286c697374290a20202020666f72205f69642c207265736f7572636520696e207265736f75726365732e6974656d7328293a0a2020202020202020696620280a2020202020202020202020207265736f757263652e69642e6765745f656e746974795f747970652829203d3d20227374643a3a46696c65220a2020202020202020202020206f72207265736f757263652e69642e6765745f656e746974795f747970652829203d3d20227374643a3a4469726563746f7279220a2020202020202020293a0a2020202020202020202020207065725f686f73745b7265736f757263652e6d6f64656c2e686f73745d2e617070656e64287265736f75726365290a0a20202020202020206966207265736f757263652e69642e6765745f656e746974795f747970652829203d3d20227374643a3a4469726563746f7279223a0a2020202020202020202020207065725f686f73745f646972735b7265736f757263652e6d6f64656c2e686f73745d2e617070656e64287265736f75726365290a0a2020202023206e6f772061646420646570732070657220686f73740a20202020666f7220686f73742c2066696c657320696e207065725f686f73742e6974656d7328293a0a2020202020202020666f72206866696c6520696e2066696c65733a0a202020202020202020202020666f72207064697220696e207065725f686f73745f646972735b686f73745d3a0a20202020202020202020202020202020696620280a20202020202020202020202020202020202020206866696c652e7061746820213d20706469722e706174680a2020202020202020202020202020202020202020616e64206866696c652e706174685b3a206c656e28706469722e70617468295d203d3d20706469722e706174680a20202020202020202020202020202020293a0a202020202020202020202020202020202020202023204d616b65207468652046696c65207265736f75726365207265717569726520746865206469726563746f72790a20202020202020202020202020202020202020206866696c652e72657175697265732e6164642870646972290a0a0a646566206765745f70617373776f7264732870775f66696c65293a0a202020207265636f726473203d207b7d0a202020206966206f732e706174682e6578697374732870775f66696c65293a0a202020202020202077697468206f70656e2870775f66696c652c20227222292061732066643a0a202020202020202020202020666f72206c696e6520696e2066642e726561646c696e657328293a0a202020202020202020202020202020206c696e65203d206c696e652e737472697028290a202020202020202020202020202020206966206c656e286c696e6529203e20323a0a202020202020202020202020202020202020202069203d206c696e652e696e64657828223d22290a0a20202020202020202020202020202020202020207472793a0a2020202020202020202020202020202020202020202020207265636f7264735b6c696e655b3a695d2e737472697028295d203d206c696e655b69202b2031203a5d2e737472697028290a20202020202020202020202020202020202020206578636570742056616c75654572726f723a0a202020202020202020202020202020202020202020202020706173730a0a2020202072657475726e207265636f7264730a0a0a64656620736176655f70617373776f7264732870775f66696c652c207265636f726473293a0a2020202077697468206f70656e2870775f66696c652c2022772b22292061732066643a0a2020202020202020666f72206b65792c2076616c756520696e207265636f7264732e6974656d7328293a0a20202020202020202020202066642e7772697465282225733d25735c6e22202520286b65792c2076616c756529290a0a0a40706c7567696e0a6465662067656e65726174655f70617373776f7264280a20202020636f6e746578743a20436f6e746578742c2070775f69643a2022737472696e67222c206c656e6774683a2022696e7422203d2032300a29202d3e2022737472696e67223a0a202020202222220a2020202047656e65726174652061206e65772072616e646f6d2070617373776f726420616e642073746f726520697420696e207468652064617461206469726563746f7279206f66207468650a2020202070726f6a6563742e204f6e206e65787420696e766f636174696f6e73207468652073746f7265642070617373776f72642077696c6c20626520757365642e0a0a202020203a706172616d2070775f69643a20546865206964206f66207468652070617373776f726420746f206964656e746966792069742e0a202020203a706172616d206c656e6774683a20546865206c656e677468206f66207468652070617373776f72642c2064656661756c74206c656e6774682069732032300a202020202222220a20202020646174615f646972203d20636f6e746578742e6765745f646174615f64697228290a2020202070775f66696c65203d206f732e706174682e6a6f696e28646174615f6469722c202270617373776f726466696c652e74787422290a0a20202020696620223d2220696e2070775f69643a0a2020202020202020726169736520457863657074696f6e28225468652070617373776f72642069642063616e6e6f7420636f6e7461696e203d22290a0a202020207265636f726473203d206765745f70617373776f7264732870775f66696c65290a0a2020202069662070775f696420696e207265636f7264733a0a202020202020202072657475726e207265636f7264735b70775f69645d0a0a20202020726e64203d2072616e646f6d2e53797374656d52616e646f6d28290a202020207077203d2022220a202020207768696c65206c656e28707729203c206c656e6774683a0a202020202020202078203d2063687228726e642e72616e64696e742833332c2031323629290a202020202020202069662072652e6d6174636828225b412d5a612d7a302d395d222c207829206973206e6f74204e6f6e653a0a2020202020202020202020207077202b3d20780a0a20202020232073746f726520746865206e65772076616c75650a202020207265636f7264735b70775f69645d203d2070770a20202020736176655f70617373776f7264732870775f66696c652c207265636f726473290a0a2020202072657475726e2070770a0a0a40706c7567696e0a6465662070617373776f726428636f6e746578743a20436f6e746578742c2070775f69643a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657472696576652074686520676976656e2070617373776f72642066726f6d20612070617373776f72642066696c652e2049742072616973657320616e20657863657074696f6e207768656e20612070617373776f7264206973206e6f7420666f756e640a0a202020203a706172616d2070775f69643a20546865206964206f66207468652070617373776f726420746f206964656e746966792069742e0a202020202222220a20202020646174615f646972203d20636f6e746578742e6765745f646174615f64697228290a2020202070775f66696c65203d206f732e706174682e6a6f696e28646174615f6469722c202270617373776f726466696c652e74787422290a0a20202020696620223d2220696e2070775f69643a0a2020202020202020726169736520457863657074696f6e28225468652070617373776f72642069642063616e6e6f7420636f6e7461696e203d22290a0a202020207265636f726473203d206765745f70617373776f7264732870775f66696c65290a0a2020202069662070775f696420696e207265636f7264733a0a202020202020202072657475726e207265636f7264735b70775f69645d0a0a20202020656c73653a0a2020202020202020726169736520457863657074696f6e282250617373776f726420257320646f6573206e6f7420657869737420696e2066696c65202573222025202870775f69642c2070775f66696c6529290a0a0a40706c7567696e28227072696e7422290a646566207072696e7466286d6573736167653a206f626a656374207c205265666572656e6365293a0a202020202222220a202020205072696e742074686520676976656e206d65737361676520746f207374646f75740a202020202222220a202020207072696e74286d657373616765290a0a0a40706c7567696e0a646566207265706c61636528737472696e673a2022737472696e67222c206f6c643a2022737472696e67222c206e65773a2022737472696e672229202d3e2022737472696e67223a0a2020202072657475726e20737472696e672e7265706c616365286f6c642c206e6577290a0a0a4064657072656361746564287265706c616365645f62793d2274686520603d3d602062696e617279206f70657261746f7222290a40706c7567696e0a64656620657175616c7328617267313a2022616e79222c20617267323a2022616e79222c20646573633a2022737472696e6722203d204e6f6e65293a0a202020202222220a20202020436f6d70617265206172673120616e6420617267320a202020202222220a202020206966206172673120213d20617267323a0a202020202020202069662064657363206973206e6f74204e6f6e653a0a202020202020202020202020726169736520417373657274696f6e4572726f722822257320213d2025733a2025732220252028617267312c20617267322c206465736329290a2020202020202020656c73653a0a202020202020202020202020726169736520417373657274696f6e4572726f722822257320213d2025732220252028617267312c206172673229290a0a0a40706c7567696e282261737365727422290a646566206173736572745f66756e6374696f6e2865787072657373696f6e3a2022626f6f6c222c206d6573736167653a2022737472696e6722203d202222293a0a202020202222220a20202020526169736520617373657274696f6e206572726f722069662065787072657373696f6e2069732066616c73650a202020202222220a202020206966206e6f742065787072657373696f6e3a0a2020202020202020726169736520417373657274696f6e4572726f722822417373657274696f6e206572726f723a2022202b206d657373616765290a0a0a4064657072656361746564287265706c616365645f62793d227573696e672061206c69737420636f6d70726568656e73696f6e22290a40706c7567696e0a6465662073656c656374286f626a656374733a20226c697374222c20617474723a2022737472696e672229202d3e20226c697374223a0a202020202222220a2020202052657475726e2061206c6973742077697468207468652073656c65637420617474726962757465730a202020202222220a2020202072657475726e205b67657461747472286974656d2c20617474722920666f72206974656d20696e206f626a656374735d0a0a0a40706c7567696e0a646566206974656d286f626a656374733a20226c697374222c20696e6465783a2022696e742229202d3e20226c697374223a0a202020202222220a2020202052657475726e2061206c69737420746861742073656c6563747320746865206974656d20617420696e6465782066726f6d2065616368206f6620746865207375626c697374730a202020202222220a2020202072203d205b5d0a20202020666f72206f626a20696e206f626a656374733a0a2020202020202020722e617070656e64286f626a5b696e6465785d290a0a2020202072657475726e20720a0a0a40706c7567696e0a646566206b65795f736f7274286974656d733a20226c697374222c206b65793a2022616e792229202d3e20226c697374223a0a202020202222220a20202020536f727420616e206172726179206f66206f626a656374206f6e206b65790a202020202222220a202020206966206973696e7374616e6365286b65792c207475706c65293a0a202020202020202072657475726e20736f72746564286974656d732c206b65793d61747472676574746572282a6b657929290a0a2020202072657475726e20736f72746564286974656d732c206b65793d61747472676574746572286b657929290a0a0a40706c7567696e0a6465662074696d657374616d702864756d6d793a2022616e7922203d204e6f6e6529202d3e2022696e74223a0a202020202222220a2020202052657475726e20616e20696e74656765722077697468207468652063757272656e7420756e69782074696d657374616d700a0a202020203a706172616d20616e793a20412064756d6d7920617267756d656e7420746f2062652061626c6520746f2075736520746869732066756e6374696f6e20617320612066696c7465720a202020202222220a2020202072657475726e20696e742874696d652e74696d652829290a0a0a40706c7567696e0a646566206361706974616c697a6528737472696e673a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a202020204361706974616c697a652074686520676976656e20737472696e670a202020202222220a2020202072657475726e20737472696e672e6361706974616c697a6528290a0a0a40706c7567696e0a64656620757070657228737472696e673a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657475726e206120636f7079206f662074686520737472696e67207769746820616c6c20746865206361736564206368617261637465727320636f6e76657274656420746f207570706572636173652e0a202020202222220a2020202072657475726e20737472696e672e757070657228290a0a0a40706c7567696e0a646566206c6f77657228737472696e673a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657475726e206120636f7079206f662074686520737472696e67207769746820616c6c20746865206361736564206368617261637465727320636f6e76657274656420746f206c6f776572636173652e0a202020202222220a2020202072657475726e20737472696e672e6c6f77657228290a0a0a40706c7567696e0a646566206c696d697428737472696e673a2022737472696e67222c206c656e6774683a2022696e742229202d3e2022737472696e67223a0a202020202222224c696d697420746865206c656e67746820666f722074686520737472696e670a0a202020203a706172616d20737472696e673a2054686520737472696e6720746f206c696d697420746865206c656e677468206f66660a202020203a706172616d206c656e6774683a20546865206d6178206c656e677468206f662074686520737472696e670a202020202222220a2020202072657475726e20737472696e675b3a6c656e6774685d0a0a0a40706c7567696e0a6465662074797065286f626a3a2022616e792229202d3e2022616e79223a0a2020202076616c7565203d206f626a2e76616c75650a2020202072657475726e2076616c75652e7479706528292e5f5f646566696e6974696f6e5f5f0a0a0a40706c7567696e0a6465662073657175656e636528693a2022696e74222c2073746172743a2022696e7422203d203029202d3e20226c697374223a0a202020202222220a2020202052657475726e20612073657175656e6365206f662069206e756d626572732c207374617274696e672066726f6d207a65726f206f7220737461727420696620737570706c6965642e0a0a202020203a706172616d20693a20546865206e756d626572206f6620656c656d656e747320696e207468652073657175656e63652e0a202020203a706172616d2073746172743a20546865207374617274696e672076616c756520666f72207468652073657175656e63652e0a0a202020203a72657475726e3a2041206c69737420636f6e7461696e696e67207468652073657175656e6365206f6620696e74732e0a202020202222220a2020202072657475726e206c6973742872616e67652873746172742c20696e74286929202b20737461727429290a0a0a40706c7567696e0a64656620696e6c696e65696628636f6e646974696f6e616c3a2022626f6f6c222c20613a2022616e79222c20623a2022616e792229202d3e2022616e79223a0a202020202222220a20202020416e20696e6c696e652069660a202020202222220a20202020696620636f6e646974696f6e616c3a0a202020202020202072657475726e20610a2020202072657475726e20620a0a0a40706c7567696e0a646566206174286f626a656374733a2053657175656e63655b6f626a656374207c205265666572656e63655d2c20696e6465783a2022696e742229202d3e206f626a656374207c205265666572656e63653a0a202020202222220a2020202047657420746865206974656d20617420696e6465780a202020202222220a2020202072657475726e206f626a656374735b696e7428696e646578295d0a0a0a40706c7567696e0a6465662061747472286f626a3a2022616e79222c20617474723a2022737472696e672229202d3e206f626a656374207c205265666572656e63653a0a2020202072657475726e206765746174747228616c6c6f775f7265666572656e63655f76616c756573286f626a292c2061747472290a0a0a40706c7567696e0a6465662069737365742876616c75653a2022616e792229202d3e2022626f6f6c223a0a202020202222220a2020202052657475726e73207472756520696620612076616c756520686173206265656e207365740a202020202222220a2020202072657475726e2076616c7565206973206e6f74204e6f6e650a0a0a40706c7567696e0a646566206f626a69642876616c75653a2022616e792229202d3e2022737472696e67223a0a2020202072657475726e20737472280a2020202020202020280a20202020202020202020202076616c75652e5f6765745f696e7374616e636528292c0a2020202020202020202020207374722869642876616c75652e5f6765745f696e7374616e6365282929292c0a20202020202020202020202076616c75652e5f6765745f696e7374616e636528292e5f5f636c6173735f5f2c0a2020202020202020290a20202020290a0a0a40706c7567696e0a64656620636f756e74286974656d5f6c6973743a2053657175656e63655b6f626a656374207c205265666572656e63655d29202d3e2022696e74223a0a202020202222220a2020202052657475726e7320746865206e756d626572206f6620656c656d656e747320696e2074686973206c6973742e0a0a20202020496620616e7920756e6b6e6f776e73206172652070726573656e7420696e20746865206c6973742c20636f756e7473207468656d206c696b6520616e79206f746865722076616c75652e20446570656e64696e67206f6e2074686520756e6b6e6f776e2073656d616e7469637320696e20796f75720a202020206d6f64656c2074686973206d61792070726f6475636520616e20696e616363757261746520636f756e742e20466f72206120636f756e74207468617420697320636f6e7365727661746976652077697468207265737065637420746f20756e6b6e6f776e732c2073656520606c656e602e0a202020202222220a2020202072657475726e206c656e286974656d5f6c697374290a0a0a40706c7567696e28226c656e22290a646566206c6973745f6c656e286974656d5f6c6973743a2053657175656e63655b6f626a656374207c205265666572656e63655d29202d3e2022696e74223a0a202020202222220a2020202052657475726e7320746865206e756d626572206f6620656c656d656e747320696e2074686973206c6973742e20556e6c696b652060636f756e74602c207468697320706c7567696e20697320636f6e736572766174697665207768656e20697420636f6d657320746f20756e6b6e6f776e2076616c7565732e0a20202020496620616e7920756e6b6e6f776e2069732070726573656e7420696e20746865206c6973742c2074686520726573756c7420697320616c736f20756e6b6e6f776e2e0a202020202222220a20202020756e6b6e6f776e3a204f7074696f6e616c5b556e6b6e6f776e5d203d206e657874280a2020202020202020286974656d20666f72206974656d20696e206974656d5f6c697374206966206973696e7374616e6365286974656d2c20556e6b6e6f776e29292c204e6f6e650a20202020290a2020202072657475726e206c656e286974656d5f6c6973742920696620756e6b6e6f776e206973204e6f6e6520656c736520556e6b6e6f776e28736f757263653d756e6b6e6f776e2e736f75726365290a0a0a40706c7567696e0a64656620756e69717565286974656d5f6c6973743a20226c6973742229202d3e2022626f6f6c223a0a202020202222220a2020202052657475726e73207472756520696620616c6c206974656d7320696e20746869732073657175656e63652061726520756e697175650a202020202222220a202020207365656e203d2073657428290a20202020666f72206974656d20696e206974656d5f6c6973743a0a20202020202020206966206974656d20696e207365656e3a0a20202020202020202020202072657475726e2046616c73650a20202020202020207365656e2e616464286974656d290a0a2020202072657475726e20547275650a0a0a40706c7567696e0a64656620666c617474656e286974656d5f6c6973743a20226c6973742229202d3e20226c697374223a0a202020202222220a20202020466c617474656e2074686973206c6973740a202020202222220a2020202072657475726e206c69737428636861696e2e66726f6d5f6974657261626c65286974656d5f6c69737429290a0a0a40706c7567696e0a6465662073706c697428737472696e675f6c6973743a2022737472696e67222c2064656c696d3a2022737472696e672229202d3e20226c697374223a0a202020202222220a2020202053706c69742074686520676976656e20737472696e6720696e746f2061206c6973740a0a202020203a706172616d20737472696e675f6c6973743a20546865206c69737420746f2073706c697420696e746f2070617274730a202020203a706172616d2064656c696d3a205468652064656c696d6574657220746f2073706c69742074686520746578742062790a202020202222220a2020202072657475726e20737472696e675f6c6973742e73706c69742864656c696d290a0a0a6465662064657465726d696e655f70617468286374782c206d6f64756c655f6469722c2070617468293a0a202020202222220a2020202044657465726d696e6520746865207265616c2070617468206261736564206f6e2074686520676976656e20706174680a202020202222220a2020202070617468203d205f657874656e645f70617468286374782c2070617468290a202020207061727473203d20706174682e73706c6974286f732e706174682e736570290a0a202020206d6f64756c6573203d2050726f6a6563742e67657428292e6d6f64756c65730a0a2020202069662070617274735b305d203d3d2022223a0a20202020202020206d6f64756c655f70617468203d2050726f6a6563742e67657428292e70726f6a6563745f706174680a20202020656c69662070617274735b305d206e6f7420696e206d6f64756c65733a0a2020202020202020726169736520457863657074696f6e28224d6f64756c6520257320646f6573206e6f7420657869737420666f722070617468202573222025202870617274735b305d2c207061746829290a20202020656c73653a0a20202020202020206d6f64756c655f70617468203d206d6f64756c65735b70617274735b305d5d2e5f706174680a0a2020202072657475726e206f732e706174682e6a6f696e286d6f64756c655f706174682c206d6f64756c655f6469722c206f732e706174682e7365702e6a6f696e2870617274735b313a5d29290a0a0a646566206765745f66696c655f636f6e74656e74286374782c206d6f64756c655f6469722c2070617468293a0a202020202222220a202020204765742074686520636f6e74656e7473206f6620612066696c650a202020202222220a2020202066696c656e616d65203d2064657465726d696e655f70617468286374782c206d6f64756c655f6469722c2070617468290a0a2020202069662066696c656e616d65206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822257320646f6573206e6f742065786973742220252070617468290a0a202020206966206e6f74206f732e706174682e697366696c652866696c656e616d65293a0a2020202020202020726169736520457863657074696f6e282225732069736e277420612076616c69642066696c6520282573292220252028706174682c2066696c656e616d6529290a0a2020202066696c655f6664203d206f70656e2866696c656e616d652c20227222290a2020202069662066696c655f6664206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822556e61626c6520746f206f70656e2066696c652025732220252066696c656e616d65290a0a20202020636f6e74656e74203d2066696c655f66642e7265616428290a2020202066696c655f66642e636c6f736528290a0a2020202072657475726e20636f6e74656e740a0a0a40706c7567696e0a64656620736f75726365286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657475726e20746865207465787475616c20636f6e74656e7473206f662074686520676976656e2066696c650a202020202222220a2020202072657475726e206765745f66696c655f636f6e74656e74286374782c202266696c6573222c2070617468290a0a0a636c6173732046696c654d61726b657228737472293a0a202020202222220a202020204d61726b657220636c61737320746f20696e6469636174652074686174207468697320737472696e672069732061637475616c6c792061207265666572656e636520746f20612066696c65206f6e206469736b2e0a0a2020202054686973206d656368616e69736d206973206261636b7761726420636f6d70617469626c65207769746820746865206f6c6420696e2d62616e64206d656368616e69736d2e0a0a20202020546f20706173732066696c65207265666572656e6365732066726f6d206f74686572206d6f64756c65732c20796f752063616e20636f7079207061737465207468697320636c61737320696e746f20796f7572206f776e206d6f64756c652e0a20202020546865206d61746368696e6720696e207468652066696c652068616e646c65722069733a0a0a20202020202020206966202246696c654d61726b65722220696e20636f6e74656e742e5f5f636c6173735f5f2e5f5f6e616d655f5f0a0a202020202222220a0a20202020646566205f5f6e65775f5f28636c732c2066696c656e616d65293a0a20202020202020206f626a203d207374722e5f5f6e65775f5f28636c732c2022696d702d6d6f64756c652d736f757263653a66696c653a2f2f22202b2066696c656e616d65290a20202020202020206f626a2e66696c656e616d65203d2066696c656e616d650a202020202020202072657475726e206f626a0a0a0a40706c7567696e0a6465662066696c65286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657475726e20746865207465787475616c20636f6e74656e7473206f662074686520676976656e2066696c650a202020202222220a2020202066696c656e616d65203d2064657465726d696e655f70617468286374782c202266696c6573222c2070617468290a0a2020202069662066696c656e616d65206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822257320646f6573206e6f742065786973742220252070617468290a0a202020206966206e6f74206f732e706174682e697366696c652866696c656e616d65293a0a2020202020202020726169736520457863657074696f6e282225732069736e277420612076616c69642066696c652220252066696c656e616d65290a0a2020202072657475726e2046696c654d61726b6572286f732e706174682e616273706174682866696c656e616d6529290a0a0a40706c7567696e0a6465662066616d696c796f66286d656d6265723a20227374643a3a4f53222c2066616d696c793a2022737472696e672229202d3e2022626f6f6c223a0a202020202222220a2020202044657465726d696e65206966206d656d6265722069732061206d656d626572206f662074686520676976656e206f7065726174696e672073797374656d2066616d696c790a202020202222220a202020206966206d656d6265722e6e616d65203d3d2066616d696c793a0a202020202020202072657475726e20547275650a0a20202020706172656e74203d206d656d6265720a202020207472793a0a20202020202020207768696c6520706172656e742e66616d696c79206973206e6f74204e6f6e653a0a202020202020202020202020696620706172656e742e6e616d65203d3d2066616d696c793a0a2020202020202020202020202020202072657475726e20547275650a0a202020202020202020202020706172656e74203d20706172656e742e66616d696c790a20202020657863657074204f7074696f6e616c56616c7565457863657074696f6e3a0a2020202020202020706173730a0a2020202072657475726e2046616c73650a0a0a666163745f6361636865203d207b7d0a0a0a40706c7567696e0a6465662067657466616374280a20202020636f6e746578743a20436f6e746578742c207265736f757263653a2022616e79222c20666163745f6e616d653a2022737472696e67222c2064656661756c745f76616c75653a2022616e7922203d204e6f6e650a29202d3e2022616e79223a0a202020202222220a20202020526574726965766520612066616374206f662074686520676976656e207265736f757263650a202020202222220a202020207265736f757263655f6964203d20696e6d616e74612e7265736f75726365732e746f5f6964287265736f75726365290a202020206966207265736f757263655f6964206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e282246616374732063616e206f6e6c79206265207265747265697665642066726f6d207265736f75726365732e22290a0a2020202023205370656369616c206361736520666f7220756e69742074657374696e6720616e64206d6f636b696e670a202020206966206861736174747228636f6e746578742e636f6d70696c65722c202272656673222920616e64202266616374732220696e20636f6e746578742e636f6d70696c65722e726566733a0a2020202020202020696620280a2020202020202020202020207265736f757263655f696420696e20636f6e746578742e636f6d70696c65722e726566735b226661637473225d0a202020202020202020202020616e6420666163745f6e616d6520696e20636f6e746578742e636f6d70696c65722e726566735b226661637473225d5b7265736f757263655f69645d0a2020202020202020293a0a20202020202020202020202072657475726e20636f6e746578742e636f6d70696c65722e726566735b226661637473225d5b7265736f757263655f69645d5b666163745f6e616d655d0a0a2020202020202020666163745f76616c7565203d20556e6b6e6f776e28736f757263653d7265736f75726365290a2020202020202020756e6b6e6f776e5f706172616d65746572732e617070656e64280a2020202020202020202020207b227265736f75726365223a207265736f757263655f69642c2022706172616d65746572223a20666163745f6e616d652c2022736f75726365223a202266616374227d0a2020202020202020290a0a202020202020202069662064656661756c745f76616c7565206973206e6f74204e6f6e653a0a20202020202020202020202072657475726e2064656661756c745f76616c75650a202020202020202072657475726e20666163745f76616c75650a202020202320456e64207370656369616c20636173650a0a202020207472793a0a2020202020202020636c69656e74203d20636f6e746578742e6765745f636c69656e7428290a0a2020202020202020656e76203d20436f6e6669672e6765742822636f6e666967222c2022656e7669726f6e6d656e74222c204e6f6e65290a2020202020202020696620656e76206973204e6f6e653a0a202020202020202020202020726169736520457863657074696f6e280a202020202020202020202020202020202254686520656e7669726f6e6d656e74206f662074686973206d6f64656c2073686f756c6420626520636f6e6669677572656420696e20636f6e6669673e656e7669726f6e6d656e74220a202020202020202020202020290a0a202020202020202023206c6f61642063616368650a20202020202020206966206e6f7420666163745f63616368653a0a0a2020202020202020202020206465662063616c6c28293a0a2020202020202020202020202020202072657475726e20636c69656e742e6c6973745f706172616d73280a20202020202020202020202020202020202020207469643d656e762c0a20202020202020202020202020202020290a0a202020202020202020202020726573756c74203d20636f6e746578742e72756e5f73796e632863616c6c290a202020202020202020202020696620726573756c742e636f6465203d3d203230303a0a20202020202020202020202020202020666163745f76616c756573203d20726573756c742e726573756c745b22706172616d6574657273225d0a20202020202020202020202020202020666f7220666163745f76616c756520696e20666163745f76616c7565733a0a2020202020202020202020202020202020202020666163745f63616368652e73657464656661756c7428666163745f76616c75655b227265736f757263655f6964225d2c207b7d295b0a202020202020202020202020202020202020202020202020666163745f76616c75655b226e616d65225d0a20202020202020202020202020202020202020205d203d20666163745f76616c75655b2276616c7565225d0a0a20202020202020202320617474656d7074206361636865206869740a20202020202020206966207265736f757263655f696420696e20666163745f63616368653a0a202020202020202020202020696620666163745f6e616d6520696e20666163745f63616368655b7265736f757263655f69645d3a0a2020202020202020202020202020202072657475726e20666163745f63616368655b7265736f757263655f69645d5b666163745f6e616d655d0a0a2020202020202020666163745f76616c7565203d204e6f6e650a0a20202020202020206465662063616c6c28293a0a20202020202020202020202072657475726e20636c69656e742e6765745f706172616d287469643d656e762c2069643d666163745f6e616d652c207265736f757263655f69643d7265736f757263655f6964290a0a2020202020202020726573756c74203d20636f6e746578742e72756e5f73796e632863616c6c290a0a2020202020202020696620726573756c742e636f6465203d3d203230303a0a202020202020202020202020666163745f76616c7565203d20726573756c742e726573756c745b22706172616d65746572225d5b2276616c7565225d0a2020202020202020656c73653a0a2020202020202020202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e696e666f280a2020202020202020202020202020202022506172616d202573206f66207265736f7572636520257320697320756e6b6e6f776e222c20666163745f6e616d652c207265736f757263655f69640a202020202020202020202020290a202020202020202020202020666163745f76616c7565203d20556e6b6e6f776e28736f757263653d7265736f75726365290a202020202020202020202020756e6b6e6f776e5f706172616d65746572732e617070656e64280a202020202020202020202020202020207b227265736f75726365223a207265736f757263655f69642c2022706172616d65746572223a20666163745f6e616d652c2022736f75726365223a202266616374227d0a202020202020202020202020290a0a2020202065786365707420436f6e6e656374696f6e526566757365644572726f723a0a20202020202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e7761726e696e67280a20202020202020202020202022506172616d202573206f66207265736f7572636520257320697320756e6b6e6f776e206265636175736520636f6e6e656374696f6e20746f20736572766572207761732072656675736564222c0a202020202020202020202020666163745f6e616d652c0a2020202020202020202020207265736f757263655f69642c0a2020202020202020290a2020202020202020666163745f76616c7565203d20556e6b6e6f776e28736f757263653d7265736f75726365290a2020202020202020756e6b6e6f776e5f706172616d65746572732e617070656e64280a2020202020202020202020207b227265736f75726365223a207265736f757263655f69642c2022706172616d65746572223a20666163745f6e616d652c2022736f75726365223a202266616374227d0a2020202020202020290a0a202020206966206973696e7374616e636528666163745f76616c75652c20556e6b6e6f776e2920616e642064656661756c745f76616c7565206973206e6f74204e6f6e653a0a202020202020202072657475726e2064656661756c745f76616c75650a0a2020202072657475726e20666163745f76616c75650a0a0a40706c7567696e0a64656620656e7669726f6e6d656e742829202d3e2022737472696e67223a0a202020202222220a2020202052657475726e2074686520656e7669726f6e6d656e742069640a202020202222220a20202020656e76203d20436f6e6669672e6765742822636f6e666967222c2022656e7669726f6e6d656e74222c204e6f6e65290a0a20202020696620656e76206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e280a2020202020202020202020202254686520656e7669726f6e6d656e74206f662074686973206d6f64656c2073686f756c6420626520636f6e6669677572656420696e20636f6e6669673e656e7669726f6e6d656e74220a2020202020202020290a0a2020202072657475726e2073747228656e76290a0a0a40706c7567696e0a64656620656e7669726f6e6d656e745f6e616d65286374783a20436f6e7465787429202d3e2022737472696e67223a0a202020202222220a2020202052657475726e20746865206e616d65206f662074686520656e7669726f6e6d656e742028617320646566696e6564206f6e2074686520736572766572290a202020202222220a20202020656e76203d20656e7669726f6e6d656e7428290a0a202020206465662063616c6c28293a0a202020202020202072657475726e206374782e6765745f636c69656e7428292e6765745f656e7669726f6e6d656e742869643d656e76290a0a20202020726573756c74203d206374782e72756e5f73796e632863616c6c290a20202020696620726573756c742e636f646520213d203230303a0a202020202020202072657475726e20556e6b6e6f776e28736f757263653d656e76290a2020202072657475726e20726573756c742e726573756c745b22656e7669726f6e6d656e74225d5b226e616d65225d0a0a0a40706c7567696e0a64656620656e7669726f6e6d656e745f736572766572286374783a20436f6e7465787429202d3e2022737472696e67223a0a202020202222220a2020202052657475726e207468652061646472657373206f6620746865206d616e6167656d656e74207365727665720a202020202222220a20202020636c69656e74203d206374782e6765745f636c69656e7428290a202020207365727665725f75726c203d20636c69656e742e5f7472616e73706f72745f696e7374616e63652e5f6765745f636c69656e745f636f6e66696728290a202020206d61746368203d2072652e73656172636828225e687474705b735d3f3a2f2f285b5e3a5d2b293a222c207365727665725f75726c290a202020206966206d61746368206973206e6f74204e6f6e653a0a202020202020202072657475726e206d617463682e67726f75702831290a2020202072657475726e20556e6b6e6f776e28736f757263653d7365727665725f75726c290a0a0a40706c7567696e0a646566207365727665725f63612829202d3e2022737472696e67223a0a2020202066696c656e616d65203d20436f6e6669672e6765742822636f6d70696c65725f726573745f7472616e73706f7274222c202273736c5f63615f636572745f66696c65222c204e6f6e65290a202020206966206e6f742066696c656e616d653a0a202020202020202072657475726e2022220a0a202020206966206e6f74206f732e706174682e697366696c652866696c656e616d65293a0a2020202020202020726169736520457863657074696f6e282225732069736e277420612076616c69642066696c652220252066696c656e616d65290a0a2020202066696c655f6664203d206f70656e2866696c656e616d652c20227222290a2020202069662066696c655f6664206973204e6f6e653a0a2020202020202020726169736520457863657074696f6e2822556e61626c6520746f206f70656e2066696c652025732220252066696c656e616d65290a0a20202020636f6e74656e74203d2066696c655f66642e7265616428290a2020202072657475726e20636f6e74656e740a0a0a40706c7567696e0a646566207365727665725f73736c2829202d3e2022626f6f6c223a0a2020202072657475726e20436f6e6669672e6765742822636f6d70696c65725f726573745f7472616e73706f7274222c202273736c222c2046616c7365290a0a0a40706c7567696e0a646566207365727665725f746f6b656e28636f6e746578743a20436f6e746578742c20636c69656e745f74797065733a2022737472696e675b5d22203d205b226167656e74225d29202d3e2022737472696e67223a0a20202020746f6b656e203d20436f6e6669672e6765742822636f6d70696c65725f726573745f7472616e73706f7274222c2022746f6b656e222c204e6f6e65290a202020206966206e6f7420746f6b656e3a0a202020202020202072657475726e2022220a0a202020202320526571756573742061206e657720746f6b656e20666f722074686973206167656e740a20202020746f6b656e203d2022220a202020207472793a0a2020202020202020636c69656e74203d20636f6e746578742e6765745f636c69656e7428290a0a2020202020202020656e76203d20436f6e6669672e6765742822636f6e666967222c2022656e7669726f6e6d656e74222c204e6f6e65290a2020202020202020696620656e76206973204e6f6e653a0a202020202020202020202020726169736520457863657074696f6e280a202020202020202020202020202020202254686520656e7669726f6e6d656e74206f662074686973206d6f64656c2073686f756c6420626520636f6e6669677572656420696e20636f6e6669673e656e7669726f6e6d656e74220a202020202020202020202020290a0a20202020202020206465662063616c6c28293a0a20202020202020202020202072657475726e20636c69656e742e6372656174655f746f6b656e280a202020202020202020202020202020207469643d656e762c20636c69656e745f74797065733d6c69737428636c69656e745f7479706573292c206964656d706f74656e743d547275650a202020202020202020202020290a0a2020202020202020726573756c74203d20636f6e746578742e72756e5f73796e632863616c6c290a0a2020202020202020696620726573756c742e636f6465203d3d203230303a0a202020202020202020202020746f6b656e203d20726573756c742e726573756c745b22746f6b656e225d0a2020202020202020656c73653a0a2020202020202020202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e7761726e696e672822556e61626c6520746f206765742061206e657720746f6b656e22290a202020202020202020202020726169736520457863657074696f6e2822556e61626c6520746f2067657420612076616c696420746f6b656e22290a2020202065786365707420436f6e6e656374696f6e526566757365644572726f723a0a20202020202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e657863657074696f6e2822556e61626c6520746f206765742061206e657720746f6b656e22290a2020202020202020726169736520457863657074696f6e2822556e61626c6520746f2067657420612076616c696420746f6b656e22290a0a2020202072657475726e20746f6b656e0a0a0a40706c7567696e0a646566207365727665725f706f72742829202d3e2022696e74223a0a2020202072657475726e20436f6e6669672e6765742822636f6d70696c65725f726573745f7472616e73706f7274222c2022706f7274222c2038383838290a0a0a40706c7567696e0a646566206765745f656e76286e616d653a2022737472696e67222c2064656661756c745f76616c75653a2022737472696e673f22203d204e6f6e6529202d3e2022737472696e67223a0a202020202222220a2020202047657420616e20656e7669726f6e6d656e74207661726961626c652c2072657475726e20556e6b6e6f776e20696620697420646f65736e27742065786973742e0a20202020416c736f206c6f672061207761726e696e6720746f2073686f7720746865206d697373696e6720656e7669726f6e6d656e74207661726961626c652e0a0a202020203a706172616d206b65793a20546865206e616d65206f662074686520656e7669726f6e6d656e74207661726961626c6520746f206765740a202020202222220a2020202076616c203d206f732e676574656e76286e616d652c2064656661756c745f76616c7565290a2020202069662076616c206973206e6f74204e6f6e653a0a202020202020202072657475726e2076616c0a0a202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e7761726e696e67280a202020202020202022456e7669726f6e6d656e74207661726961626c6520257320646f65736e27742065786973742c2072657475726e696e6720556e6b6e6f776e28736f757263653d25732920696e7374656164222c0a20202020202020206e616d652c0a202020202020202072657072286e616d65292c0a20202020290a2020202072657475726e20556e6b6e6f776e28736f757263653d6e616d65290a0a0a4064657072656361746564287265706c616365645f62793d22696e74287374643a3a6765745f656e76282e2e2e292922290a40706c7567696e0a646566206765745f656e765f696e74286e616d653a2022737472696e67222c2064656661756c745f76616c75653a2022696e743f22203d204e6f6e6529202d3e2022696e74223a0a2020202023205468697320706c7567696e2077696c6c2072656d61696e2c20627574206974206973207265636f6d6d656e64656420746f2075736520676574656e760a202020202320696e73746561640a2020202076616c3a20737472207c20696e74207c204e6f6e65203d206f732e676574656e76286e616d652c2064656661756c745f76616c7565290a2020202069662076616c206973206e6f74204e6f6e653a0a202020202020202072657475726e20696e742876616c290a0a202020206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f292e7761726e696e67280a202020202020202022456e7669726f6e6d656e74207661726961626c6520257320646f65736e27742065786973742c2072657475726e696e6720556e6b6e6f776e28736f757263653d25732920696e7374656164222c0a20202020202020206e616d652c0a202020202020202072657072286e616d65292c0a20202020290a2020202072657475726e20556e6b6e6f776e28736f757263653d6e616d65290a0a0a40706c7567696e0a6465662069735f696e7374616e6365286374783a20436f6e746578742c206f626a3a2022616e79222c20636c733a2022737472696e672229202d3e2022626f6f6c223a0a2020202074203d206374782e6765745f7479706528636c73290a202020207472793a0a2020202020202020742e76616c6964617465286f626a2e5f6765745f696e7374616e63652829290a202020206578636570742052756e74696d65457863657074696f6e3a0a202020202020202072657475726e2046616c73650a2020202072657475726e20547275650a0a0a40706c7567696e0a646566206c656e6774682876616c75653a2022737472696e672229202d3e2022696e74223a0a202020202222220a2020202052657475726e20746865206c656e677468206f662074686520737472696e670a202020202222220a2020202072657475726e206c656e2876616c7565290a0a0a4064657072656361746564287265706c616365645f62793d227573696e672061206c69737420636f6d70726568656e73696f6e22290a40706c7567696e0a6465662066696c7465722876616c7565733a20226c697374222c206e6f745f6974656d3a20227374643a3a456e746974792229202d3e20226c697374223a0a202020202222220a2020202046696c746572206e6f745f6974656d2066726f6d2076616c7565730a202020202222220a2020202072657475726e205b7820666f72207820696e2076616c756573206966207820213d206e6f745f6974656d5d0a0a0a4064657072656361746564287265706c616365645f62793d227573696e672074686520603c646963743e5b3c6b65793e5d6020636f6e73747275637422290a40706c7567696e0a64656620646963745f676574286463743a202264696374222c206b65793a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202047657420616e20656c656d656e742066726f6d2074686520646963742e2052616973657320616e20657863657074696f6e207768656e20746865206b6579206973206e6f7420666f756e6420696e2074686520646963740a202020202222220a2020202072657475726e206463745b6b65795d0a0a0a4064657072656361746564287265706c616365645f62793d2274686520603c6b65793e20696e203c646963743e6020636f6e73747275637422290a40706c7567696e0a64656620636f6e7461696e73286463743a202264696374222c206b65793a2022737472696e672229202d3e2022626f6f6c223a0a202020202222220a20202020436865636b206966206b65792065786973747320696e206463742e0a202020202222220a2020202072657475726e206b657920696e206463740a0a0a40706c7567696e282267657461747472222c20616c6c6f775f756e6b6e6f776e3d54727565290a64656620676574617474726962757465280a20202020656e746974793a20227374643a3a456e74697479222c0a202020206174747269627574655f6e616d653a2022737472696e67222c0a2020202064656661756c745f76616c75653a206f626a656374207c205265666572656e6365203d204e6f6e652c0a202020206e6f5f756e6b6e6f776e3a2022626f6f6c22203d20547275652c0a29202d3e206f626a656374207c205265666572656e63653a0a202020202222220a2020202052657475726e207468652076616c7565206f662074686520676976656e206174747269627574652e204966207468652061747472696275746520646f6573206e6f742065786973742c2072657475726e207468652064656661756c742076616c75652e0a0a202020203a61747472206e6f5f756e6b6e6f776e3a205768656e207468697320617267756d656e742069732073657420746f20747275652c2074686973206d6574686f642077696c6c2072657475726e207468652064656661756c742076616c7565207768656e20746865206174747269627574650a20202020202020202020202020202020202020202020697320756e6b6e6f776e2e0a202020202222220a202020207472793a0a202020202020202076616c7565203d206765746174747228616c6c6f775f7265666572656e63655f76616c75657328656e74697479292c206174747269627574655f6e616d65290a20202020202020206966206973696e7374616e63652876616c75652c20556e6b6e6f776e2920616e64206e6f5f756e6b6e6f776e3a0a20202020202020202020202072657475726e2064656661756c745f76616c75650a202020202020202072657475726e2076616c75650a2020202065786365707420284e6f74466f756e64457863657074696f6e2c204b65794572726f72293a0a202020202020202072657475726e2064656661756c745f76616c75650a0a0a4064657072656361746564287265706c616365645f62793d2274686520606e6f746020756e617279206f70657261746f7222290a40706c7567696e0a64656620696e766572742876616c75653a2022626f6f6c2229202d3e2022626f6f6c223a0a202020202222220a20202020496e76657274206120626f6f6c65616e2076616c75650a202020202222220a2020202072657475726e206e6f742076616c75650a0a0a40706c7567696e0a646566206c6973745f66696c6573286374783a20436f6e746578742c20706174683a2022737472696e672229202d3e20226c697374223a0a202020202222220a202020204c6973742066696c657320696e2061206469726563746f72790a202020202222220a2020202070617468203d2064657465726d696e655f70617468286374782c202266696c6573222c2070617468290a2020202072657475726e205b6620666f72206620696e206f732e6c697374646972287061746829206966206f732e706174682e697366696c65286f732e706174682e6a6f696e28706174682c206629295d0a0a0a40706c7567696e28616c6c6f775f756e6b6e6f776e3d54727565290a6465662069735f756e6b6e6f776e2876616c75653a206f626a656374207c205265666572656e636529202d3e2022626f6f6c223a0a2020202072657475726e206973696e7374616e63652876616c75652c20556e6b6e6f776e290a0a0a40706c7567696e0a6465662076616c69646174655f74797065280a2020202066715f747970655f6e616d653a2022737472696e67222c2076616c75653a2022616e79222c2076616c69646174696f6e5f706172616d65746572733a20226469637422203d204e6f6e650a29202d3e2022626f6f6c223a0a202020202222220a20202020436865636b2077686574686572206076616c756560207361746973666965732074686520636f6e73747261696e7473206f662074797065206066715f747970655f6e616d65602e205768656e2074686520676976656e2074797065202866715f747970655f6e616d65290a2020202072657175697265732076616c69646174696f6e5f706172616d65746572732c20746865792063616e2062652070726f7669646564207573696e6720746865206f7074696f6e616c206076616c69646174696f6e5f706172616d65746572736020617267756d656e742e0a0a2020202054686520666f6c6c6f77696e6720747970657320726571756972652076616c69646174696f6e5f706172616d65746572733a0a0a20202020202020202a20707964616e7469632e636f6e646563696d616c3a0a20202020202020202020202067743a20446563696d616c203d204e6f6e650a20202020202020202020202067653a20446563696d616c203d204e6f6e650a2020202020202020202020206c743a20446563696d616c203d204e6f6e650a2020202020202020202020206c653a20446563696d616c203d204e6f6e650a2020202020202020202020206d61785f6469676974733a20696e74203d204e6f6e650a202020202020202020202020646563696d616c5f706c616365733a20696e74203d204e6f6e650a2020202020202020202020206d756c7469706c655f6f663a20446563696d616c203d204e6f6e650a20202020202020202a20707964616e7469632e636f6e666c6f617420616e6420707964616e7469632e636f6e696e743a0a20202020202020202020202067743a20666c6f6174203d204e6f6e650a20202020202020202020202067653a20666c6f6174203d204e6f6e650a2020202020202020202020206c743a20666c6f6174203d204e6f6e650a2020202020202020202020206c653a20666c6f6174203d204e6f6e650a2020202020202020202020206d756c7469706c655f6f663a20666c6f6174203d204e6f6e652c0a20202020202020202a20707964616e7469632e636f6e7374723a0a2020202020202020202020206d696e5f6c656e6774683a20696e74203d204e6f6e650a2020202020202020202020206d61785f6c656e6774683a20696e74203d204e6f6e650a2020202020202020202020206375727461696c5f6c656e6774683a20696e74203d204e6f6e6520284f6e6c792076657269667920746865207265676578206f6e20746865206669727374206375727461696c5f6c656e6774682063686172616374657273290a20202020202020202020202072656765783a20737472203d204e6f6e65202020202020202020202854686520726567657820697320766572696669656420766961205061747465726e2e6d617463682829290a0a202020204578616d706c652075736167653a0a0a20202020202020202a20446566696e65206120766c616e5f6964207479706520776869636820726570726573656e7420612076616c696420766c616e2049442028302d342c303935293a0a0a202020202020202020207479706564656620766c616e5f6964206173206e756d626572206d61746368696e67207374643a3a76616c69646174655f747970652822707964616e7469632e636f6e696e74222c2073656c662c207b226765223a20302c20226c65223a20343039357d290a202020202222220a202020207472793a0a2020202020202020696d706f727420696e6d616e74612e76616c69646174696f6e5f747970650a20202020657863657074204d6f64756c654e6f74466f756e644572726f723a0a202020202020202023205765206172652072756e6e696e6720616761696e737420612076657273696f6e206f6620696e6d616e74612d636f7265207468617420646f65736e27742068617665207468652076616c69646174696f6e5f74797065206d6574686f64207965742e0a2020202020202020232046616c6c6261636b20746f20746865206f6c6420696d706c656d656e746174696f6e2e0a202020202020202072657475726e205f76616c69646174655f747970655f6c65676163792866715f747970655f6e616d652c2076616c75652c2076616c69646174696f6e5f706172616d6574657273290a20202020656c73653a0a202020202020202023205573652076616c69646174655f7479706520696d706c656d656e746174696f6e2066726f6d20696e6d616e74612d636f72650a2020202020202020756e777261707065645f76616c7565203d2070726f78792e44796e616d696350726f78792e756e777261702876616c7565290a20202020202020206966206973696e7374616e636528756e777261707065645f76616c75652c204e6f6e6556616c7565293a0a202020202020202020202020756e777261707065645f76616c7565203d204e6f6e650a20202020202020207472793a0a202020202020202020202020696e6d616e74612e76616c69646174696f6e5f747970652e76616c69646174655f74797065280a2020202020202020202020202020202066715f747970655f6e616d652c20756e777261707065645f76616c75652c2076616c69646174696f6e5f706172616d65746572730a202020202020202020202020290a20202020202020206578636570742028707964616e7469632e56616c69646174696f6e4572726f722c2056616c75654572726f72293a0a20202020202020202020202072657475726e2046616c73650a202020202020202072657475726e20547275650a0a0a646566205f76616c69646174655f747970655f6c6567616379280a2020202066715f747970655f6e616d653a2022737472696e67222c2076616c75653a2022616e79222c2076616c69646174696f6e5f706172616d65746572733a20226469637422203d204e6f6e650a29202d3e2022626f6f6c223a0a202020202222220a2020202054686973206d6574686f6420636f6e7461696e7320746865206f6c6420696d706c656d656e746174696f6e206f66207468652076616c69646174655f7479706520706c7567696e20666f72206261636b776172647320636f6d7061746962696c69747920726561736f6e2e0a202020202222220a202020206966206e6f7420280a202020202020202066715f747970655f6e616d652e737461727473776974682822707964616e7469632e22290a20202020202020206f722066715f747970655f6e616d652e7374617274737769746828226461746574696d652e22290a20202020202020206f722066715f747970655f6e616d652e7374617274737769746828226970616464726573732e22290a20202020202020206f722066715f747970655f6e616d652e737461727473776974682822757569642e22290a20202020293a0a202020202020202072657475726e2046616c73650a202020206d6f64756c655f6e616d652c20747970655f6e616d65203d2066715f747970655f6e616d652e73706c697428222e222c2031290a202020206d6f64756c65203d20696d706f72746c69622e696d706f72745f6d6f64756c65286d6f64756c655f6e616d65290a2020202074203d2067657461747472286d6f64756c652c20747970655f6e616d65290a202020202320436f6e73747275637420707964616e746963206d6f64656c0a2020202069662076616c69646174696f6e5f706172616d6574657273206973206e6f74204e6f6e653a0a20202020202020206d6f64656c203d20707964616e7469632e6372656174655f6d6f64656c280a20202020202020202020202066715f747970655f6e616d652c2076616c75653d2874282a2a76616c69646174696f6e5f706172616d6574657273292c202e2e2e290a2020202020202020290a20202020656c73653a0a20202020202020206d6f64656c203d20707964616e7469632e6372656174655f6d6f64656c2866715f747970655f6e616d652c2076616c75653d28742c202e2e2e29290a202020202320446f2076616c69646174696f6e0a202020207472793a0a20202020202020206d6f64656c2876616c75653d76616c7565290a2020202065786365707420707964616e7469632e56616c69646174696f6e4572726f723a0a202020202020202072657475726e2046616c73650a0a2020202072657475726e20547275650a0a0a40706c7567696e0a6465662069735f6261736536345f656e636f64656428733a2022737472696e672229202d3e2022626f6f6c223a0a202020202222220a20202020436865636b20776865746865722074686520676976656e20737472696e672069732062617365363420656e636f6465642e0a202020202222220a202020207472793a0a2020202020202020656e636f6465645f737472203d20732e656e636f646528227574662d3822290a20202020202020206261736536342e6236346465636f646528656e636f6465645f7374722c2076616c69646174653d54727565290a2020202065786365707420457863657074696f6e3a0a202020202020202072657475726e2046616c73650a2020202072657475726e20547275650a0a0a40706c7567696e0a64656620686f73746e616d65286671646e3a2022737472696e672229202d3e2022737472696e67223a0a202020202222220a2020202052657475726e2074686520686f73746e616d652070617274206f6620746865206671646e0a202020202222220a2020202072657475726e206671646e2e73706c697428222e22295b305d0a0a0a40706c7567696e0a646566207072656669786c656e6774685f746f5f6e65746d61736b287072656669786c656e3a2022696e742229202d3e20227374643a3a697076345f61646472657373223a0a202020202222220a20202020476976656e20746865207072656669786c656e6774682c2072657475726e20746865206e65746d61736b0a202020202222220a20202020696e74657266616365203d206970616464726573732e69705f696e746572666163652866223235352e3235352e3235352e3235352f7b7072656669786c656e7d22290a2020202072657475726e2073747228696e746572666163652e6e65746d61736b290a0a0a40706c7567696e0a646566207072656669786c656e28616464723a20227374643a3a6970765f616e795f696e746572666163652229202d3e2022696e74223a0a202020202222220a2020202052657475726e20746865207072656669786c656e206f662074686520434944520a0a20202020466f7220696e7374616e63653a0a20202020202020207c207374643a3a7072696e74287072656669786c656e28223139322e3136382e312e3130302f323422292920202d2d3e202032340a202020202222220a20202020696e74657266616365203d206970616464726573732e69705f696e746572666163652861646472290a0a2020202072657475726e20696e746572666163652e6e6574776f726b2e7072656669786c656e0a0a0a40706c7567696e0a646566206e6574776f726b5f6164647265737328616464723a20227374643a3a6970765f616e795f696e746572666163652229202d3e20227374643a3a6970765f616e795f61646472657373223a0a202020202222220a2020202052657475726e20746865206e6574776f726b2061646472657373206f662074686520434944520a0a20202020466f7220696e7374616e63653a0a20202020202020207c207374643a3a7072696e74286e6574776f726b5f6164647265737328223139322e3136382e312e3130302f323422292920202d2d3e20203139322e3136382e312e300a202020202222220a20202020696e74657266616365203d206970616464726573732e69705f696e746572666163652861646472290a0a2020202072657475726e2073747228696e746572666163652e6e6574776f726b2e6e6574776f726b5f61646472657373290a0a0a40706c7567696e0a646566206e65746d61736b28616464723a20227374643a3a6970765f616e795f696e746572666163652229202d3e20227374643a3a6970765f616e795f61646472657373223a0a202020202222220a2020202052657475726e20746865206e65746d61736b206f662074686520434944520a0a20202020466f7220696e7374616e63653a0a20202020202020207c207374643a3a7072696e74286e65746d61736b28223139322e3136382e312e3130302f3234222929202020202d2d3e20203235352e3235352e3235352e300a202020202222220a20202020696e74657266616365203d206970616464726573732e69705f696e746572666163652861646472290a0a2020202072657475726e2073747228696e746572666163652e6e6574776f726b2e6e65746d61736b290a0a0a40706c7567696e0a646566206970696e646578280a20202020616464723a20227374643a3a6970765f616e795f6e6574776f726b222c20706f736974696f6e3a2022696e74222c206b6565705f7072656669783a2022626f6f6c22203d2046616c73650a29202d3e2022737472696e67223a0a202020202222220a2020202052657475726e20746865206164647265737320617420706f736974696f6e20696e20746865206e6574776f726b2e0a0a202020203a706172616d20616464723a20546865206e6574776f726b20616464726573730a202020203a706172616d20706f736974696f6e3a20546865206465736972656420706f736974696f6e206f662074686520616464726573730a202020203a706172616d206b6565705f7072656669783a20496620746865207072656669782073686f756c6420626520696e636c7564656420696e2074686520726573756c740a202020202222220a202020206e6574203d206970616464726573732e69705f6e6574776f726b2861646472290a2020202061646472657373203d20737472286e65745b706f736974696f6e5d290a0a202020206966206b6565705f7072656669783a0a202020202020202072657475726e2066227b616464726573737d2f7b6e65742e7072656669786c656e7d220a2020202072657475726e20616464726573730a0a0a40706c7567696e0a646566206164645f746f5f697028616464723a20227374643a3a6970765f616e795f61646472657373222c206e3a2022696e742229202d3e20227374643a3a6970765f616e795f61646472657373223a0a202020202222220a202020204164642061206e756d62657220746f2074686520676976656e2069702e0a202020202222220a2020202072657475726e20737472286970616464726573732e69705f61646472657373286164647229202b206e290a0a0a40706c7567696e0a6465662069705f616464726573735f66726f6d5f696e74657266616365280a2020202069705f696e746572666163653a20227374643a3a6970765f616e795f696e74657266616365222c20202320747970653a2069676e6f72650a29202d3e20227374643a3a6970765f616e795f61646472657373223a20202320747970653a2069676e6f72650a202020202222220a2020202054616b6520616e20697020616464726573732077697468206e6574776f726b2070726566697820616e64206f6e6c792072657475726e2074686520697020616464726573730a0a202020203a706172616d2069705f696e746572666163653a2054686520696e746572666163652066726f6d2077686572652077652077696c6c20657874726163742074686520697020616464726573730a202020202222220a2020202072657475726e20737472286970616464726573732e69705f696e746572666163652869705f696e74657266616365292e6970290a0a0a40706c7567696e0a646566206a736f6e5f6c6f61647328733a2022737472696e672229202d3e2022616e79223a0a202020202222220a20202020446573657269616c697a65207320286120737472696e6720696e7374616e636520636f6e7461696e696e672061204a534f4e20646f63756d656e742920746f20616e20696e6d616e74612064736c206f626a6563742e0a0a202020203a706172616d20733a205468652073657269616c697a6564206a736f6e20737472696e6720746f2070617273652e0a202020202222220a2020202072657475726e206a736f6e2e6c6f6164732873290a0a0a40706c7567696e0a646566206a736f6e5f64756d7073286f626a3a2022616e792229202d3e2022737472696e67223a0a202020202222220a2020202053657269616c697a65206f626a20746f2061204a534f4e20666f726d617474656420737472696e672e0a0a202020203a706172616d206f626a3a2054686520696e6d616e7461206f626a65637420746861742073686f756c642062652073657269616c697a6564206173206a736f6e2e0a202020202222220a2020202072657475726e206a736f6e2e64756d7073286f626a2c2064656661756c743d7574696c2e696e7465726e616c5f6a736f6e5f656e636f646572290a0a0a40706c7567696e0a64656620666f726d6174285f5f737472696e673a2022737472696e67222c202a617267733a2022616e79222c202a2a6b77617267733a2022616e792229202d3e2022737472696e67223a0a202020202222220a20202020466f726d6174206120737472696e67207573696e6720707974686f6e20737472696e6720666f726d61747465722c20616e6420616363657074696e672073746174656d656e74732077686963680a202020206e617469766520696e6d616e746120662d737472696e6720646f65736e277420737570706f727420287375636820617320616363657373696e6720646963742076616c756573290a0a202020203a706172616d205f5f737472696e673a2054686520737472696e6720746f206170706c7920666f726d617474696e6720746f0a202020203a706172616d20617267733a2054686520706f736974696f6e616c20617267756d656e747320746f206665656420696e746f2074686520607374722e666f726d617460206d6574686f640a202020203a706172616d206b77617267733a20546865206b6579776f726420617267756d656e747320746f206665656420696e746f2074686520607374722e666f726d617460206d6574686f640a202020202222220a2020202072657475726e205f5f737472696e672e666f726d6174282a617267732c202a2a6b7761726773290a0a0a7472793a0a2020202066726f6d20696e6d616e74612e706c7567696e7320696d706f7274204d6f64656c547970650a2020202066726f6d20696e6d616e74612e7265666572656e63657320696d706f7274205265666572656e63652c207265666572656e63650a0a20202020407265666572656e636528227374643a3a496e745265666572656e636522290a20202020636c61737320496e745265666572656e6365285265666572656e63655b696e745d293a0a202020202020202022222241207265666572656e6365207468617420636f6e76657274732061207265666572656e63652076616c756520746f20616e20696e742222220a0a2020202020202020646566205f5f696e69745f5f2873656c662c2076616c75653a206f626a656374207c205265666572656e636529202d3e204e6f6e653a0a2020202020202020202020202222220a2020202020202020202020203a706172616d2076616c75653a20546865207265666572656e6365206f722076616c756520746f20636f6e766572742e0a2020202020202020202020202222220a202020202020202020202020737570657228292e5f5f696e69745f5f28290a20202020202020202020202073656c662e76616c7565203d2076616c75650a0a2020202020202020646566207265736f6c76652873656c662c206c6f676765723a204c6f6767657241424329202d3e20696e743a0a2020202020202020202020202222225265736f6c766520746865207265666572656e63652222220a2020202020202020202020206c6f676765722e64656275672822436f6e76657274696e67207265666572656e63652076616c756520746f20696e7422290a20202020202020202020202076616c7565203d20696e742873656c662e7265736f6c76655f6f746865722873656c662e76616c75652c206c6f6767657229290a20202020202020202020202072657475726e2076616c75650a0a2020202040706c7567696e0a20202020646566206372656174655f696e745f7265666572656e63652876616c75653a206f626a656374207c205265666572656e636529202d3e205265666572656e63655b696e745d3a0a202020202020202072657475726e20496e745265666572656e63652876616c7565290a0a20202020407265666572656e636528227374643a3a456e7669726f6e6d656e7422290a20202020636c61737320456e7669726f6e6d656e745265666572656e6365285265666572656e63655b7374725d293a0a202020202020202022222241207265666572656e636520746f20666574636820656e7669726f6e6d656e74207661726961626c65732222220a0a2020202020202020646566205f5f696e69745f5f2873656c662c206e616d653a20737472207c205265666572656e63655b7374725d29202d3e204e6f6e653a0a2020202020202020202020202222220a2020202020202020202020203a706172616d206e616d653a20546865206e616d65206f662074686520656e7669726f6e6d656e74207661726961626c652e0a2020202020202020202020202222220a202020202020202020202020737570657228292e5f5f696e69745f5f28290a20202020202020202020202073656c662e6e616d65203d206e616d650a0a2020202020202020646566207265736f6c76652873656c662c206c6f676765723a204c6f6767657241424329202d3e207374723a0a2020202020202020202020202222225265736f6c766520746865207265666572656e63652222220a202020202020202020202020656e765f7661725f6e616d65203d2073656c662e7265736f6c76655f6f746865722873656c662e6e616d652c206c6f67676572290a2020202020202020202020206c6f676765722e646562756728225265736f6c76696e6720656e7669726f6e6d656e74207661726961626c652025286e616d652973222c206e616d653d73656c662e6e616d65290a20202020202020202020202076616c7565203d206f732e676574656e7628656e765f7661725f6e616d65290a20202020202020202020202069662076616c7565206973204e6f6e653a0a202020202020202020202020202020207261697365204c6f6f6b75704572726f72286622456e7669726f6e6d656e74207661726961626c65207b656e765f7661725f6e616d657d206973206e6f742073657422290a20202020202020202020202072657475726e2076616c75650a0a2020202020202020646566205f5f65715f5f2873656c662c2076616c75653a206f626a65637429202d3e20626f6f6c3a0a2020202020202020202020206d617463682076616c75653a0a202020202020202020202020202020206361736520456e7669726f6e6d656e745265666572656e636528293a0a202020202020202020202020202020202020202072657475726e2073656c662e6e616d65203d3d2076616c75652e6e616d650a2020202020202020202020202020202063617365205f3a0a202020202020202020202020202020202020202072657475726e2046616c73650a0a2020202040706c7567696e0a20202020646566206372656174655f656e7669726f6e6d656e745f7265666572656e6365286e616d653a20737472207c205265666572656e63655b7374725d29202d3e205265666572656e63655b7374725d3a0a202020202020202022222243726561746520616e20656e7669726f6e6d656e74207265666572656e63650a0a20202020202020203a706172616d206e616d653a20546865206e616d65206f6620746865207661726961626c6520746f2066657463682066726f6d2074686520656e7669726f6e6d656e740a20202020202020203a72657475726e3a2041207265666572656e636520746f20776861742063616e206265207265736f6c76656420746f206120737472696e670a20202020202020202222220a202020202020202072657475726e20456e7669726f6e6d656e745265666572656e6365286e616d653d6e616d65290a0a20202020407265666572656e636528227374643a3a466163745265666572656e636522290a20202020636c61737320466163745265666572656e6365285265666572656e63655b7374725d293a0a20202020202020202222220a202020202020202041207265666572656e636520746f20612066616374206f662061207265736f757263650a202020202020202054686520646966666572656e6365207769746820606765746661637460206973207468617420776520646f6e2774206e6565642061207265636f6d70696c650a20202020202020202020202073696e636520746865207265736f6c7665206973206f6e6c7920646f6e6520647572696e6720746865206465706c6f79206f6620746865207265736f757263650a20202020202020204974206f6e6c7920776f726b73207769746820612072656d6f7465206f7263686573747261746f72206f722069662077652073657420606d6f636b65645f6661637473600a20202020202020202222220a0a2020202020202020646566205f5f696e69745f5f280a20202020202020202020202073656c662c0a202020202020202020202020656e7669726f6e6d656e743a207374722c0a2020202020202020202020207265736f757263655f69643a207374722c0a202020202020202020202020666163745f6e616d653a207374722c0a2020202020202020202020206d6f636b65645f66616374733a2064696374207c204e6f6e652c0a202020202020202029202d3e204e6f6e653a0a202020202020202020202020737570657228292e5f5f696e69745f5f28290a20202020202020202020202073656c662e656e7669726f6e6d656e74203d20656e7669726f6e6d656e740a20202020202020202020202073656c662e7265736f757263655f6964203d207265736f757263655f69640a20202020202020202020202073656c662e666163745f6e616d65203d20666163745f6e616d650a0a20202020202020202020202073656c662e6d6f636b65645f6661637473203d206d6f636b65645f66616374730a0a2020202020202020646566207265736f6c76652873656c662c206c6f676765723a204c6f6767657241424329202d3e207374723a0a0a2020202020202020202020206c6f676765722e696e666f280a20202020202020202020202020202020225265736f6c76696e67206661637420602528666163745f6e616d6529736020666f72207265736f75726365206025287265736f757263655f6964297360222c0a20202020202020202020202020202020666163745f6e616d653d73656c662e666163745f6e616d652c0a202020202020202020202020202020207265736f757263655f69643d73656c662e7265736f757263655f69642c0a202020202020202020202020290a0a20202020202020202020202023205370656369616c206361736520666f7220756e69742074657374696e6720616e64206d6f636b696e670a20202020202020202020202069662073656c662e6d6f636b65645f6661637473206973206e6f74204e6f6e653a0a2020202020202020202020202020202069662073656c662e7265736f757263655f696420696e2073656c662e6d6f636b65645f66616374733a0a202020202020202020202020202020202020202072657475726e2073656c662e6d6f636b65645f66616374735b73656c662e7265736f757263655f69645d5b73656c662e666163745f6e616d655d0a20202020202020202020202020202020656c73653a0a20202020202020202020202020202020202020207261697365204c6f6f6b75704572726f72280a20202020202020202020202020202020202020202020202066224469646e27742066696e64206661637420607b73656c662e666163745f6e616d657d6020666f72207265736f7572636520607b73656c662e7265736f757263655f69647d60220a2020202020202020202020202020202020202020290a2020202020202020202020202320456e64207370656369616c20636173650a0a202020202020202020202020636c69656e74203d20656e64706f696e74732e53796e63436c69656e7428226167656e7422290a202020202020202020202020726573756c74203d20636c69656e742e6765745f6661637473287469643d73656c662e656e7669726f6e6d656e742c207269643d73656c662e7265736f757263655f6964290a0a202020202020202020202020666f72206661637420696e20726573756c742e6765745f726573756c7428295b2264617461225d3a0a20202020202020202020202020202020696620666163745b226e616d65225d203d3d2073656c662e666163745f6e616d653a0a202020202020202020202020202020202020202072657475726e20666163745b2276616c7565225d0a0a2020202020202020202020207261697365204c6f6f6b75704572726f72280a2020202020202020202020202020202066224469646e27742066696e64206661637420607b73656c662e666163745f6e616d657d6020666f72207265736f7572636520607b73656c662e7265736f757263655f69647d60220a202020202020202020202020290a0a2020202020202020646566205f5f7374725f5f2873656c6629202d3e207374723a0a20202020202020202020202072657475726e206622466163745265666572656e63655b7265736f757263655f69643d7b73656c662e7265736f757263655f69647d2c666163745f6e616d653d7b73656c662e666163745f6e616d657d5d220a0a2020202040706c7567696e0a20202020646566206372656174655f666163745f7265666572656e6365280a2020202020202020636f6e746578743a20436f6e746578742c0a20202020202020207265736f757263653a20747970696e672e416e6e6f74617465645b70726f78792e44796e616d696350726f78792c204d6f64656c547970655b227374643a3a5265736f75726365225d5d2c0a2020202020202020666163745f6e616d653a207374722c0a2020202029202d3e20466163745265666572656e63653a0a202020202020202022222243726561746520612066616374207265666572656e63650a20202020202020203a706172616d207265736f757263653a20546865207265736f75726365207468617420636f6e7461696e732074686520666163740a20202020202020203a706172616d20666163745f6e616d653a20546865206e616d65206f662074686520666163740a20202020202020203a72657475726e3a2041207265666572656e636520746f20776861742063616e206265207265736f6c76656420746f206120737472696e670a0a2020202020202020696620636f6e746578742e7265667320657869737473206974206d65616e73207468617420736f6d65206661637473206d69676874206265206d6f636b65642c0a2020202020202020736f2077652070617373207468656d20746f2074686520466163745265666572656e63650a20202020202020202222220a20202020202020207265736f757263655f6964203d20696e6d616e74612e7265736f75726365732e746f5f6964287265736f75726365290a20202020202020206966207265736f757263655f6964206973204e6f6e653a0a202020202020202020202020726169736520457863657074696f6e282246616374732063616e206f6e6c79206265207265747265697665642066726f6d207265736f75726365732e22290a0a20202020202020206d6f636b65645f6661637473203d204e6f6e650a0a202020202020202023205370656369616c206361736520666f7220756e69742074657374696e6720616e64206d6f636b696e670a2020202020202020696620280a2020202020202020202020206861736174747228636f6e746578742e636f6d70696c65722c20227265667322290a202020202020202020202020616e64202266616374732220696e20636f6e746578742e636f6d70696c65722e726566730a202020202020202020202020616e64206c656e28636f6e746578742e636f6d70696c65722e726566735b226661637473225d29203e20300a2020202020202020293a0a2020202020202020202020206d6f636b65645f6661637473203d207b0a2020202020202020202020202020202073747228726964293a20666163747320666f72207269642c20666163747320696e20636f6e746578742e636f6d70696c65722e726566735b226661637473225d2e6974656d7328290a2020202020202020202020207d0a20202020202020202320456e64207370656369616c20636173650a0a202020202020202072657475726e20466163745265666572656e6365280a202020202020202020202020656e7669726f6e6d656e743d636f6e746578742e6765745f656e7669726f6e6d656e745f696428292c0a2020202020202020202020207265736f757263655f69643d737472287265736f757263655f6964292c0a202020202020202020202020666163745f6e616d653d666163745f6e616d652c0a2020202020202020202020206d6f636b65645f66616374733d6d6f636b65645f66616374732c0a2020202020202020290a0a65786365707420496d706f72744572726f723a0a2020202023205265666572656e636520617265206e6f742079657420737570706f72746564206279207468697320636f72652076657273696f6e0a20202020706173730a
5fb3f88fdd6cb09b1d0a8358e95d6f87a696c823	\\x2222220a436f70797269676874203230323420496e6d616e74610a0a4c6963656e73656420756e6465722074686520417061636865204c6963656e73652c2056657273696f6e20322e30202874686520224c6963656e736522293b0a796f75206d6179206e6f742075736520746869732066696c652065786365707420696e20636f6d706c69616e6365207769746820746865204c6963656e73652e0a596f75206d6179206f627461696e206120636f7079206f6620746865204c6963656e73652061740a0a20202020687474703a2f2f7777772e6170616368652e6f72672f6c6963656e7365732f4c4943454e53452d322e300a0a556e6c657373207265717569726564206279206170706c696361626c65206c6177206f722061677265656420746f20696e2077726974696e672c20736f6674776172650a646973747269627574656420756e64657220746865204c6963656e7365206973206469737472696275746564206f6e20616e20224153204953222042415349532c0a574954484f55542057415252414e54494553204f5220434f4e444954494f4e53204f4620414e59204b494e442c206569746865722065787072657373206f7220696d706c6965642e0a53656520746865204c6963656e736520666f7220746865207370656369666963206c616e677561676520676f7665726e696e67207065726d697373696f6e7320616e640a6c696d69746174696f6e7320756e64657220746865204c6963656e73652e0a0a436f6e746163743a20636f646540696e6d616e74612e636f6d0a2222220a0a696d706f727420686173686c69620a696d706f7274206c6f6767696e670a696d706f727420706174686c69620a696d706f727420747970696e670a66726f6d20636f6c6c656374696f6e7320696d706f72742064656661756c74646963740a0a696d706f727420696e6d616e74615f706c7567696e732e6d69746f67656e2e6162630a0a696d706f727420696e6d616e74612e6167656e742e68616e646c65720a696d706f727420696e6d616e74612e657865637574652e70726f78790a696d706f727420696e6d616e74612e6578706f72740a696d706f727420696e6d616e74612e7265736f75726365730a66726f6d20696e6d616e74612e657865637574652e7574696c20696d706f727420556e6b6e6f776e0a66726f6d20696e6d616e74612e6578706f727420696d706f727420646570656e64656e63795f6d616e616765720a0a696620747970696e672e545950455f434845434b494e473a0a2020202066726f6d20696e6d616e74612e6578706f727420696d706f7274204d6f64656c446963742c205265736f75726365446963740a0a4c4f47474552203d206c6f6767696e672e6765744c6f67676572285f5f6e616d655f5f290a0a0a64656620686173685f66696c6528636f6e74656e743a20627974657329202d3e207374723a0a202020202222220a202020204372656174652061207368613120686173682066726f6d2074686520676976656e20636f6e74656e740a202020202222220a202020207368613173756d203d20686173686c69622e6e657728227368613122290a202020207368613173756d2e75706461746528636f6e74656e74290a0a2020202072657475726e207368613173756d2e68657864696765737428290a0a0a6465662067656e65726174655f636f6e74656e74280a20202020636f6e74656e745f6c6973743a206c6973745b696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78795d2c0a20202020736570617261746f723a207374722c0a29202d3e207374723a0a202020202222220a2020202047656e6572617465206120736f72746564206c697374206f6620636f6e74656e7420746f20707265666978206f722073756666697820612066696c652e0a0a202020203a706172616d20636f6e74656e745f6c6973743a20546865206c697374206f6620636f6e74656e74206f626a65637420746f20736f727420616e6420617070656e6420746f6765746865722e0a202020203a706172616d20736570617261746f723a2054686520737472696e6720746f2075736520746f206a6f696e20616c6c207468652070696563657320746f6765746865722e0a202020202222220a2020202072657475726e20736570617261746f722e6a6f696e280a20202020202020205b0a202020202020202020202020632e76616c75650a202020202020202020202020666f72206320696e20736f72746564280a20202020202020202020202020202020636f6e74656e745f6c6973742c0a202020202020202020202020202020206b65793d6c616d62646120633a20632e76616c756520696620632e736f7274696e675f6b6579206973204e6f6e6520656c736520632e736f7274696e675f6b65792c0a202020202020202020202020290a20202020202020205d0a20202020290a0a0a6465662073746f72655f66696c65280a202020206578706f727465723a20696e6d616e74612e6578706f72742e4578706f727465722c206f626a3a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78790a29202d3e207374723a0a202020202222220a2020202053746f72652074686520636f6e74656e74206f66207468652066733a3a46696c6520656e74697479206f6e207468652073657276657220616e642072657475726e207468652068617368206f66206974730a20202020636f6e74656e742e0a0a202020203a706172616d206578706f727465723a20546865206578706f7274657220746861742073686f756c64206265207573656420746f2075706c6f6164207468652066696c652e0a202020203a706172616d206f626a3a205468652066696c6520656e746974792066726f6d20746865206d6f64656c2c20696e2077686963682074686520636f6e74656e74206f66207468650a202020202020202066696c65206973206465736372696265642e0a202020202222220a20202020636f6e74656e74203d206f626a2e636f6e74656e740a202020206966206973696e7374616e636528636f6e74656e742c20556e6b6e6f776e293a0a202020202020202072657475726e20636f6e74656e740a0a202020206966202246696c654d61726b65722220696e20636f6e74656e742e5f5f636c6173735f5f2e5f5f6e616d655f5f3a0a202020202020202077697468206f70656e28636f6e74656e742e66696c656e616d652c2022726222292061732066643a0a202020202020202020202020636f6e74656e74203d2066642e7265616428290a0a202020206966206c656e286f626a2e7072656669785f636f6e74656e7429203e20303a0a2020202020202020636f6e74656e74203d20280a20202020202020202020202067656e65726174655f636f6e74656e74286f626a2e7072656669785f636f6e74656e742c206f626a2e636f6e74656e745f736570617261746f72290a2020202020202020202020202b206f626a2e636f6e74656e745f736570617261746f720a2020202020202020202020202b20636f6e74656e740a2020202020202020290a202020206966206c656e286f626a2e7375666669785f636f6e74656e7429203e20303a0a2020202020202020636f6e74656e74202b3d206f626a2e636f6e74656e745f736570657261746f72202b2067656e65726174655f636f6e74656e74280a2020202020202020202020206f626a2e7375666669785f636f6e74656e742c206f626a2e636f6e74656e745f736570617261746f720a2020202020202020290a0a2020202072657475726e206578706f727465722e75706c6f61645f66696c6528636f6e74656e74290a0a0a40696e6d616e74612e7265736f75726365732e7265736f75726365282266733a3a46696c65222c206167656e743d22686f73742e6e616d65222c2069645f6174747269627574653d227061746822290a636c6173732046696c6528696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e5265736f75726365414243293a0a202020202222220a20202020412066696c65206f6e20612066696c6573797374656d0a202020202222220a0a202020206669656c6473203d202820202320747970653a69676e6f72655b61737369676e6d656e745d0a20202020202020202270617468222c0a2020202020202020226f776e6572222c0a20202020202020202268617368222c0a20202020202020202267726f7570222c0a2020202020202020227065726d697373696f6e73222c0a20202020290a20202020706174683a207374720a202020206f776e65723a20737472207c204e6f6e650a20202020686173683a207374720a2020202067726f75703a20737472207c204e6f6e650a202020207065726d697373696f6e733a20696e74207c204e6f6e650a0a2020202040636c6173736d6574686f640a20202020646566206765745f68617368280a2020202020202020636c732c0a20202020202020206578706f727465723a20696e6d616e74612e6578706f72742e4578706f727465722c0a2020202020202020656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78792c0a2020202029202d3e207374723a0a202020202020202072657475726e2073746f72655f66696c65286578706f727465722c20656e74697479290a0a2020202040636c6173736d6574686f640a20202020646566206765745f7065726d697373696f6e73280a2020202020202020636c732c0a20202020202020205f3a20696e6d616e74612e6578706f72742e4578706f727465722c0a2020202020202020656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78792c0a2020202029202d3e20696e74207c204e6f6e653a0a202020202020202072657475726e20696e7428656e746974792e6d6f64652920696620656e746974792e6d6f6465206973206e6f74204e6f6e6520656c7365204e6f6e650a0a0a40696e6d616e74612e7265736f75726365732e7265736f75726365282266733a3a4469726563746f7279222c206167656e743d22686f73742e6e616d65222c2069645f6174747269627574653d227061746822290a636c617373204469726563746f727928696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e5265736f75726365414243293a0a202020202222220a2020202041206469726563746f7279206f6e20612066696c6573797374656d0a202020202222220a0a202020206669656c6473203d202820202320747970653a69676e6f72655b61737369676e6d656e745d0a20202020202020202270617468222c0a2020202020202020226f776e6572222c0a20202020202020202267726f7570222c0a2020202020202020227065726d697373696f6e73222c0a20202020290a20202020706174683a207374720a202020206f776e65723a20737472207c204e6f6e650a2020202067726f75703a20737472207c204e6f6e650a202020207065726d697373696f6e733a20696e74207c204e6f6e650a0a2020202040636c6173736d6574686f640a20202020646566206765745f7065726d697373696f6e73280a2020202020202020636c732c0a20202020202020205f3a20696e6d616e74612e6578706f72742e4578706f727465722c0a2020202020202020656e746974793a20696e6d616e74612e657865637574652e70726f78792e44796e616d696350726f78792c0a2020202029202d3e20696e74207c204e6f6e653a0a202020202020202072657475726e20696e7428656e746974792e6d6f64652920696620656e746974792e6d6f6465206973206e6f74204e6f6e6520656c7365204e6f6e650a0a0a40696e6d616e74612e7265736f75726365732e7265736f75726365282266733a3a53796d6c696e6b222c206167656e743d22686f73742e6e616d65222c2069645f6174747269627574653d2264737422290a636c6173732053796d6c696e6b28696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e5265736f75726365414243293a0a202020202222220a20202020412073796d626f6c6963206c696e6b206f6e207468652066696c6573797374656d0a202020202222220a0a202020206669656c6473203d202820202320747970653a69676e6f72655b61737369676e6d656e745d0a202020202020202022737263222c0a202020202020202022647374222c0a20202020290a202020207372633a207374720a202020206473743a207374720a0a0a40696e6d616e74612e6167656e742e68616e646c65722e70726f7669646572282266733a3a46696c65222c206e616d653d22706f7369785f66696c6522290a636c61737320506f73697846696c6550726f766964657228696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e48616e646c65724142435b46696c655d293a0a202020202222220a20202020546869732068616e646c65722063616e206465706c6f792066696c6573206f6e206120756e69782073797374656d0a202020202222220a0a20202020646566205f6765745f66696c652873656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c20686173683a2073747229202d3e2062797465733a0a202020202020202064617461203d2073656c662e6765745f66696c652868617368290a202020202020202069662064617461206973204e6f6e653a0a2020202020202020202020206374782e6572726f72280a202020202020202020202020202020202246696c6520776974682068617368202528686173682973206973206e6f7420617661696c61626c65206f6e20746865206f7263686573747261746f72222c0a20202020202020202020202020202020686173683d686173682c0a202020202020202020202020290a20202020202020202020202072616973652052756e74696d654572726f72282246696c65206d697373696e672066726f6d20746865206f7263686573747261746f7222290a202020202020202072657475726e20646174610a0a2020202064656620726561645f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2046696c650a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a202020202020202020202020726169736520696e6d616e74612e6167656e742e68616e646c65722e5265736f7572636550757267656428290a0a2020202020202020232072657475726e206561726c7920746f20736b697020657870656e73697665206f7065726174696f6e730a20202020202020202320436865636b207265736f757263652066726f6d2048616e646c6572436f6e746578742c206265636175736520607265736f75726365602070617373656420746f2074686973206d6574686f640a2020202020202020232077696c6c20616c7761797320686176652060707572676564602073657420746f206046616c7365602e0a20202020202020206966206374782e5f7265736f757263652e7075726765643a0a20202020202020202020202072657475726e0a0a2020202020202020666f72206b65792c2076616c756520696e2073656c662e70726f78792e66696c655f73746174287265736f757263652e70617468292e6974656d7328293a0a20202020202020202020202069662067657461747472287265736f757263652c206b657929206973206e6f74204e6f6e653a0a2020202020202020202020202020202023204f6e6c7920636f6d706172652077697468207468652063757272656e74207374617465206966207468652064657369726564207374617465206861730a2020202020202020202020202020202023206120646573697265642076616c756520666f7220746865206174747269627574650a2020202020202020202020202020202073657461747472287265736f757263652c206b65792c2076616c7565290a0a20202020202020207265736f757263652e68617368203d2073656c662e70726f78792e686173685f66696c65287265736f757263652e70617468290a0a20202020646566206372656174655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2046696c650a2020202029202d3e204e6f6e653a0a202020202020202069662073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a202020202020202020202020726169736520457863657074696f6e280a20202020202020202020202020202020662243616e6e6f74206372656174652066696c65207b7265736f757263652e706174687d2c206265636175736520697420616c7265616479206578697374732e220a202020202020202020202020290a0a202020202020202064617461203d2073656c662e5f6765745f66696c65286374782c207265736f757263652e68617368290a2020202020202020696620686173685f66696c6528646174612920213d207265736f757263652e686173683a0a202020202020202020202020726169736520457863657074696f6e28662246696c65206861736820776173207b7265736f757263652e686173687d206578706563746564207b686173685f66696c652864617461297d22290a0a202020202020202073656c662e70726f78792e707574287265736f757263652e706174682c2064617461290a0a20202020202020206966207265736f757263652e7065726d697373696f6e73206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a20202020202020206966207265736f757263652e6f776e6572206973206e6f74204e6f6e65206f72207265736f757263652e67726f7570206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f6372656174656428290a0a202020206465662064656c6574655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2046696c650a2020202029202d3e204e6f6e653a0a202020202020202069662073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a20202020202020202020202073656c662e70726f78792e72656d6f7665287265736f757263652e70617468290a20202020202020206374782e7365745f70757267656428290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c206368616e6765733a20646963742c207265736f757263653a2046696c650a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a202020202020202020202020726169736520457863657074696f6e280a20202020202020202020202020202020662243616e6e6f74207570646174652066696c65207b7265736f757263652e706174687d206265636175736520697420646f65736e2774206578697374220a202020202020202020202020290a0a202020202020202069662022686173682220696e206368616e6765733a0a20202020202020202020202064617461203d2073656c662e5f6765745f66696c65286374782c207265736f757263652e68617368290a202020202020202020202020696620686173685f66696c6528646174612920213d207265736f757263652e686173683a0a20202020202020202020202020202020726169736520457863657074696f6e280a20202020202020202020202020202020202020202246696c65206861736820776173207b7d206578706563746564207b7d222e666f726d6174280a2020202020202020202020202020202020202020202020207265736f757263652e686173682c20686173685f66696c652864617461290a2020202020202020202020202020202020202020290a20202020202020202020202020202020290a20202020202020202020202073656c662e70726f78792e707574287265736f757263652e706174682c2064617461290a0a2020202020202020696620227065726d697373696f6e732220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a2020202020202020696620226f776e65722220696e206368616e676573206f72202267726f75702220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f7570646174656428290a0a0a40696e6d616e74612e6167656e742e68616e646c65722e70726f7669646572282266733a3a4469726563746f7279222c206e616d653d22706f7369785f6469726563746f727922290a636c617373204469726563746f727948616e646c657228696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e48616e646c65724142435b4469726563746f72795d293a0a202020202222220a20202020412068616e646c657220666f72206372656174696e67206469726563746f726965730a202020202222220a0a2020202064656620726561645f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a204469726563746f72790a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e70726f78792e66696c655f657869737473287265736f757263652e70617468293a0a202020202020202020202020726169736520696e6d616e74612e6167656e742e68616e646c65722e5265736f7572636550757267656428290a0a2020202020202020666f72206b65792c2076616c756520696e2073656c662e70726f78792e66696c655f73746174287265736f757263652e70617468292e6974656d7328293a0a20202020202020202020202069662067657461747472287265736f757263652c206b657929206973206e6f74204e6f6e653a0a2020202020202020202020202020202023204f6e6c7920636f6d706172652077697468207468652063757272656e74207374617465206966207468652064657369726564207374617465206861730a2020202020202020202020202020202023206120646573697265642076616c756520666f7220746865206174747269627574650a2020202020202020202020202020202073657461747472287265736f757263652c206b65792c2076616c7565290a0a20202020646566206372656174655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a204469726563746f72790a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e6d6b646972287265736f757263652e70617468290a0a20202020202020206966207265736f757263652e7065726d697373696f6e73206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a20202020202020206966207265736f757263652e6f776e6572206973206e6f74204e6f6e65206f72207265736f757263652e67726f7570206973206e6f74204e6f6e653a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f6372656174656428290a0a202020206465662064656c6574655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a204469726563746f72790a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e726d646972287265736f757263652e70617468290a20202020202020206374782e7365745f70757267656428290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a20202020202020206368616e6765733a20646963742c0a20202020202020207265736f757263653a204469726563746f72792c0a2020202029202d3e204e6f6e653a0a2020202020202020696620227065726d697373696f6e732220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686d6f64287265736f757263652e706174682c20737472287265736f757263652e7065726d697373696f6e7329290a0a2020202020202020696620226f776e65722220696e206368616e676573206f72202267726f75702220696e206368616e6765733a0a20202020202020202020202073656c662e70726f78792e63686f776e287265736f757263652e706174682c207265736f757263652e6f776e65722c207265736f757263652e67726f7570290a0a20202020202020206374782e7365745f7570646174656428290a0a0a40696e6d616e74612e6167656e742e68616e646c65722e70726f7669646572282266733a3a53796d6c696e6b222c206e616d653d22706f7369785f73796d6c696e6b22290a636c6173732053796d6c696e6b50726f766964657228696e6d616e74615f706c7567696e732e6d69746f67656e2e6162632e48616e646c65724142435b53796d6c696e6b5d293a0a202020202222220a20202020546869732068616e646c65722063616e206465706c6f792073796d6c696e6b73206f6e20756e69782073797374656d730a202020202222220a0a2020202064656620726561645f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2053796d6c696e6b0a2020202029202d3e204e6f6e653a0a20202020202020206966206e6f742073656c662e70726f78792e66696c655f657869737473287265736f757263652e647374293a0a202020202020202020202020726169736520696e6d616e74612e6167656e742e68616e646c65722e5265736f7572636550757267656428290a2020202020202020656c6966206e6f742073656c662e70726f78792e69735f73796d6c696e6b287265736f757263652e647374293a0a202020202020202020202020726169736520457863657074696f6e280a202020202020202020202020202020202254686520746172676574206f66207265736f7572636520257320616c72656164792065786973747320627574206973206e6f7420612073796d6c696e6b2e220a2020202020202020202020202020202025207265736f757263650a202020202020202020202020290a2020202020202020656c73653a0a2020202020202020202020207265736f757263652e737263203d2073656c662e70726f78792e726561646c696e6b287265736f757263652e647374290a0a20202020646566206372656174655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2053796d6c696e6b0a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e73796d6c696e6b287265736f757263652e7372632c207265736f757263652e647374290a20202020202020206374782e7365745f6372656174656428290a0a202020206465662064656c6574655f7265736f75726365280a202020202020202073656c662c206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c207265736f757263653a2053796d6c696e6b0a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e72656d6f7665287265736f757263652e647374290a20202020202020206374782e7365745f70757267656428290a0a20202020646566207570646174655f7265736f75726365280a202020202020202073656c662c0a20202020202020206374783a20696e6d616e74612e6167656e742e68616e646c65722e48616e646c6572436f6e746578742c0a20202020202020206368616e6765733a20646963742c0a20202020202020207265736f757263653a2053796d6c696e6b2c0a2020202029202d3e204e6f6e653a0a202020202020202073656c662e70726f78792e72656d6f7665287265736f757263652e647374290a202020202020202073656c662e70726f78792e73796d6c696e6b287265736f757263652e7372632c207265736f757263652e647374290a20202020202020206374782e7365745f7570646174656428290a0a0a40646570656e64656e63795f6d616e616765720a646566206469725f6265666f72655f66696c65286d6f64656c3a20224d6f64656c44696374222c207265736f75726365733a20225265736f757263654469637422293a0a202020202222220a20202020496620612066696c652f73796d6c696e6b2f6469726563746f727920697320646566696e6564206f6e206120686f73742c207468656e206d616b6520697420646570656e64206f6e2069747320706172656e74206469726563746f72790a202020202222220a2020202023206c6f6f70206f76657220616c6c207265736f757263657320746f2066696e642066696c657320616e6420646972730a202020207065725f686f73743a20646963745b7374722c206c6973745b7475706c655b706174686c69622e506174682c206f626a6563745d5d5d203d2064656661756c7464696374286c697374290a202020207065725f686f73745f646972733a20646963745b7374722c206c6973745b6f626a6563745d5d203d2064656661756c7464696374286c697374290a20202020666f72207265736f7572636520696e207265736f75726365732e76616c75657328293a0a20202020202020206966207265736f757263652e69642e6765745f656e746974795f74797065282920696e205b0a2020202020202020202020202266733a3a46696c65222c0a2020202020202020202020202266733a3a4469726563746f7279222c0a2020202020202020202020202266733a3a4a736f6e46696c65222c0a20202020202020205d3a0a2020202020202020202020207065725f686f73745b7265736f757263652e6d6f64656c2e686f73745d2e617070656e64280a2020202020202020202020202020202028706174686c69622e50617468287265736f757263652e70617468292c207265736f75726365290a202020202020202020202020290a0a20202020202020206966207265736f757263652e69642e6765745f656e746974795f747970652829203d3d202266733a3a53796d6c696e6b223a0a2020202020202020202020207065725f686f73745b7265736f757263652e6d6f64656c2e686f73745d2e617070656e642828706174686c69622e50617468287265736f757263652e737263292c207265736f7572636529290a2020202020202020202020207065725f686f73745b7265736f757263652e6d6f64656c2e686f73745d2e617070656e642828706174686c69622e50617468287265736f757263652e647374292c207265736f7572636529290a0a20202020202020206966207265736f757263652e69642e6765745f656e746974795f747970652829203d3d202266733a3a4469726563746f7279223a0a2020202020202020202020207065725f686f73745f646972735b7265736f757263652e6d6f64656c2e686f73745d2e617070656e64287265736f75726365290a0a2020202023206e6f772061646420646570732070657220686f73740a20202020666f7220686f73742c2066696c657320696e207065725f686f73742e6974656d7328293a0a2020202020202020666f7220706174682c206866696c6520696e2066696c65733a0a202020202020202020202020666f72207064697220696e207065725f686f73745f646972735b686f73745d3a0a20202020202020202020202020202020696620706174686c69622e5061746828706469722e706174682920696e20706174682e706172656e74733a0a2020202020202020202020202020202020202020696620706469722e7075726765643a0a2020202020202020202020202020202020202020202020206966206866696c652e7075726765643a0a20202020202020202020202020202020202020202020202020202020232054686520666f6c646572206973207075726765642c20616e6420736f206973207468652066696c652c207468652066696c652073686f756c642062650a202020202020202020202020202020202020202020202020202020202320636c65616e65642075702066697273742c207468656e2074686520666f6c6465722063616e2062652e0a20202020202020202020202020202020202020202020202020202020232054686973206973206e6f742072657175697265642061732074686520666f6c64657220776f756c64206861766520636c65616e6564207468652066696c652c0a20202020202020202020202020202020202020202020202020202020232062757420697420697320616c736f206e6f742077726f6e670a20202020202020202020202020202020202020202020202020202020706469722e72657175697265732e616464286866696c65290a202020202020202020202020202020202020202020202020656c73653a0a202020202020202020202020202020202020202020202020202020202320547279696e6720746f2063726561746520612066696c6520696e20612070757267656420666f6c6465722c20746869732063616e206e6f7420776f726b0a2020202020202020202020202020202020202020202020202020202072616973652052756e74696d654572726f72280a202020202020202020202020202020202020202020202020202020202020202066224469726563746f7279207b706469722e69647d20697320707572676564206275742061207265736f7572636520697320747279696e6720746f20220a202020202020202020202020202020202020202020202020202020202020202066226465706c6f7920736f6d657468696e6720696e2069743a207b6866696c652e69647d220a20202020202020202020202020202020202020202020202020202020290a2020202020202020202020202020202020202020656c73653a0a20202020202020202020202020202020202020202020202023204d616b65207468652046696c65207265736f75726365207265717569726520746865206469726563746f72790a2020202020202020202020202020202020202020202020206866696c652e72657175697265732e6164642870646972290a
7110eda4d09e062aa5e4a390b0a572ac0d2c0220	\\x31323334
a94a8fe5ccb19ba61c4c0873d391e987982fbbd3	\\x74657374
\.


--
-- Data for Name: inmanta_module; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.inmanta_module (name, version, environment, requirements) FROM stdin;
std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef	{inmanta-core>=8.7.0.dev,"email_validator>=1.3,<3","Jinja2>=3.1,<4","pydantic>=1.10,<3"}
fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef	{inmanta-module-mitogen,inmanta-module-std}
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
std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef	52bd7825c9c79a4bc7391ba3abf4429e3a628603	inmanta_plugins.std.resources	f
std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef	4ac629bdc461bf185971b82b4fc3dd457fba3fdd	inmanta_plugins.std.types	f
std	437b9bd2d8f7e16ce70626313fe8caf6d2e1e420	7b2d2696-253e-4661-8d06-c887d7adadef	30b3be6c2af081c7ea8594e5424428222d3c1cba	inmanta_plugins.std	f
fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef	5fb3f88fdd6cb09b1d0a8358e95d6f87a696c823	inmanta_plugins.fs.resources	f
fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef	ca7f66803b24e0b831d6728f882f5a79af2f33c2	inmanta_plugins.fs.json_file	f
fs	a8ecaac2c9448803a18a5d9e16bbd87f133a06fc	7b2d2696-253e-4661-8d06-c887d7adadef	7d6539a4d7ba19b65225673c0bc5d7601787ed2b	inmanta_plugins.fs	f
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification (id, environment, created, title, message, severity, uri, read, cleared, compile_id) FROM stdin;
68b26152-1ae6-4e03-8cf9-ec5b25b4c2ba	610b57e2-82b5-4559-9c48-e5890d2fc34e	2025-10-15 13:48:00.599913+02	Compilation failed	An exporting compile has failed	error	/api/v2/compilereport/c736b649-89eb-41e4-87e7-0c7cb5832614	f	f	c736b649-89eb-41e4-87e7-0c7cb5832614
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata, expires) FROM stdin;
b82c584a-1317-4be5-887f-529a40a5fd1d	fact1	value1	7b2d2696-253e-4661-8d06-c887d7adadef	std::testing::NullResource[localhost,name=test1]	fact	2025-10-15 13:47:36.731353+02	{}	f
589df652-c3eb-4811-881a-c47a7af07494	fact2	value2	7b2d2696-253e-4661-8d06-c887d7adadef	std::testing::NullResource[localhost,name=test2]	fact	2025-10-15 13:47:36.739115+02	{}	t
704c65ad-f2b2-40d6-923b-60236b792a1a	fact3	value3	7b2d2696-253e-4661-8d06-c887d7adadef	std::testing::NullResource[localhost,name=test3]	fact	2025-10-15 13:47:36.743168+02	{}	t
9b15d93c-c19d-4c36-a5eb-d0a2817bc4d8	parameter1	value1	7b2d2696-253e-4661-8d06-c887d7adadef		fact	2025-10-15 13:47:36.746776+02	{}	f
4b2d862a-d150-46fb-80bd-715f7f9271ff	parameter2	value2	7b2d2696-253e-4661-8d06-c887d7adadef		fact	2025-10-15 13:47:36.74983+02	{}	f
47f2f0ad-1c21-423e-98e6-52fced10957c	parameter3	value3	7b2d2696-253e-4661-8d06-c887d7adadef		fact	2025-10-15 13:47:36.752598+02	{}	f
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
60467a26-35db-4717-9fe7-db98ea3915a5	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
89ab1dd2-5604-43b4-8ad1-0dd1f5a2b9fe	2025-10-15 13:47:15.788277+02	2025-10-15 13:47:16.110021+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core inmanta-license inmanta-support	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 17.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\nFound existing installation: inmanta-license 5.0.0.dev20250528022222\nNot uninstalling inmanta-license at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-license'. No files were found to uninstall.\nFound existing installation: inmanta-support 5.0.0.dev20250528015607\nNot uninstalling inmanta-support at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-support'. No files were found to uninstall.\n	0	3d2c9309-8ca2-4151-9e5f-9859ccc659c7
2303593e-9f89-4417-a0a8-a6216b1c4fdf	2025-10-15 13:47:15.77443+02	2025-10-15 13:47:15.775623+02		Init		Using extra environment variables during compile \n	0	3d2c9309-8ca2-4151-9e5f-9859ccc659c7
e033791d-5eff-4f4c-b4ca-3e03519be6fa	2025-10-15 13:47:15.77586+02	2025-10-15 13:47:15.785086+02		Venv check		Creating new venv at /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env-py3.12\n	0	3d2c9309-8ca2-4151-9e5f-9859ccc659c7
ad9917bf-79c8-402f-a594-9bcaab182741	2025-10-15 13:47:16.111075+02	2025-10-15 13:47:31.521285+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 restbase: 2.4.3\n                                 fs: 1.1.1\n                                 mitogen: 0.2.3\n                                 std: 8.5.1\n                                 devtools: 0.2.0\n                                 netbox: 4.3.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpsg56cy3s:\n                                 Pip command: /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpsg56cy3s inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-license==5.0.0.dev20250528022222 inmanta-support==5.0.0.dev20250528015607 inmanta-core==17.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (0.2.3)\ninmanta.pip              DEBUG   Collecting inmanta-module-mitogen\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/81d/4f2106ef56f3b/inmanta_module_mitogen-0.2.4-py3-none-any.whl (18 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-license==5.0.0.dev20250528022222 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (5.0.0.dev20250528022222)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-support==5.0.0.dev20250528015607 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (5.0.0.dev20250528015607)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==17.0.0.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (17.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: click<9,>=8.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (8.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (2.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (6.0.3)\ninmanta.pip              DEBUG   Collecting cryptography<46,>=36 (from inmanta-license==5.0.0.dev20250528022222)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b6a/0e535baec27b5/cryptography-45.0.7-cp311-abi3-manylinux_2_34_x86_64.whl (4.5 MB)\ninmanta.pip              DEBUG   Requirement already satisfied: psutil<8,>=5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (7.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (6.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (0.30.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (6.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.18,>=0.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (10.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<25.1,>=21.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (25.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (25.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.12.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (80.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.18.15)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.0.44)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper==0.7.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (3.2.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (2.0.1746777265)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (0.283.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from build~=1.0->inmanta-core==17.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.32.5)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (14.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.14 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cryptography<46,>=36->inmanta-license==5.0.0.dev20250528022222) (2.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from email-validator<3,>=1->inmanta-core==17.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from email-validator<3,>=1->inmanta-core==17.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from jinja2~=3.0->inmanta-core==17.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.41.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (2.41.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (4.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from python-dateutil~=2.0->inmanta-core==17.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from ruamel.yaml~=0.17->inmanta-core==17.0.0.dev0) (0.2.14)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from typing_inspect~=0.9->inmanta-core==17.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-module-mitogen) (0.3.23)\ninmanta.pip              DEBUG   Collecting mitogen (from inmanta-module-mitogen)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/b1a/6bb09b0d9fd2f/mitogen-0.3.29-py2.py3-none-any.whl (288 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cffi>=1.14->cryptography<46,>=36->inmanta-license==5.0.0.dev20250528022222) (2.23)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (3.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2025.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4.0,>=3.2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (3.2.6)\ninmanta.pip              DEBUG   Requirement already satisfied: lia-web>=0.2.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (0.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.9.0.20251008)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (3.0.0)\ninmanta.pip              DEBUG   Collecting markdown-it-py>=2.2.0 (from rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0)\ninmanta.pip              DEBUG   Using cached https://artifacts.internal.inmanta.com/root/pypi/%2Bf/873/27c59b172c501/markdown_it_py-4.0.0-py3-none-any.whl (87 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.19.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (0.1.2)\ninmanta.pip              DEBUG   Installing collected packages: mitogen, markdown-it-py, cryptography, inmanta-module-mitogen\ninmanta.pip              DEBUG   Attempting uninstall: mitogen\ninmanta.pip              DEBUG   Found existing installation: mitogen 0.3.23\ninmanta.pip              DEBUG   Not uninstalling mitogen at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'mitogen'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: markdown-it-py\ninmanta.pip              DEBUG   Found existing installation: markdown-it-py 3.0.0\ninmanta.pip              DEBUG   Not uninstalling markdown-it-py at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'markdown-it-py'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: cryptography\ninmanta.pip              DEBUG   Found existing installation: cryptography 46.0.2\ninmanta.pip              DEBUG   Not uninstalling cryptography at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'cryptography'. No files were found to uninstall.\ninmanta.pip              DEBUG   Attempting uninstall: inmanta-module-mitogen\ninmanta.pip              DEBUG   Found existing installation: inmanta-module-mitogen 0.2.3\ninmanta.pip              DEBUG   Not uninstalling inmanta-module-mitogen at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\ninmanta.pip              DEBUG   Can't uninstall 'inmanta-module-mitogen'. No files were found to uninstall.\ninmanta.pip              DEBUG   \ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   myst-parser 4.0.1 requires markdown-it-py~=3.0, but you have markdown-it-py 4.0.0 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed cryptography-45.0.7 inmanta-module-mitogen-0.2.4 markdown-it-py-4.0.0 mitogen-0.3.29\ninmanta.module           DEBUG   Successfully installed modules for project\n                                 + mitogen: 0.2.4\n                                 - mitogen: 0.2.3\n	0	3d2c9309-8ca2-4151-9e5f-9859ccc659c7
08d38668-6977-484a-9b0c-5c4a11dcfe07	2025-10-15 13:47:32.770562+02	2025-10-15 13:47:33.834828+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp4x9udabl --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=2 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=2 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 2\nexporter       DEBUG   Committing resources took 0.018 seconds\ncompiler       DEBUG   The entire export command took 0.104 seconds\n	0	6c933079-c5ff-4ae2-b5a2-82535ea8eeda
60b4e28b-1e61-4538-84a0-f41ea33cee87	2025-10-15 13:47:31.522142+02	2025-10-15 13:47:32.61142+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmplqkcqidg --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/52bd7825c9c79a4bc7391ba3abf4429e3a628603\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/7d6539a4d7ba19b65225673c0bc5d7601787ed2b\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/ca7f66803b24e0b831d6728f882f5a79af2f33c2\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/4ac629bdc461bf185971b82b4fc3dd457fba3fdd\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/30b3be6c2af081c7ea8594e5424428222d3c1cba\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/5fb3f88fdd6cb09b1d0a8358e95d6f87a696c823\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=1 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=1 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 1\nexporter       DEBUG   Committing resources took 0.039 seconds\ncompiler       DEBUG   The entire export command took 0.126 seconds\n	0	3d2c9309-8ca2-4151-9e5f-9859ccc659c7
20738706-f783-487f-8dc0-d570acacc995	2025-10-15 13:47:32.768601+02	2025-10-15 13:47:32.769624+02		Init		Using extra environment variables during compile \n	0	6c933079-c5ff-4ae2-b5a2-82535ea8eeda
f1182bb2-1d40-4042-bf98-27c20885a8ff	2025-10-15 13:47:32.76984+02	2025-10-15 13:47:32.770263+02		Venv check		Found existing venv\n	0	6c933079-c5ff-4ae2-b5a2-82535ea8eeda
26625c5a-74f9-4e95-bcfe-22000a8a897e	2025-10-15 13:47:35.337395+02	2025-10-15 13:47:35.338099+02		Init		Using extra environment variables during compile \n	0	98c1dad8-4f4a-4b4e-b67c-b51801aca758
63149346-6b26-4be8-bc37-1d0e9961d645	2025-10-15 13:47:35.338284+02	2025-10-15 13:47:35.338691+02		Venv check		Found existing venv\n	0	98c1dad8-4f4a-4b4e-b67c-b51801aca758
11fc3e00-2ac2-4c51-bf6f-441483add354	2025-10-15 13:47:33.940762+02	2025-10-15 13:47:33.941778+02		Init		Using extra environment variables during compile add_one_resource='true'\n	0	268e2c16-5326-4898-82a6-65ee4494f6e6
ee30decc-3c80-4ed7-b91a-1fd5c3190153	2025-10-15 13:47:33.94203+02	2025-10-15 13:47:33.942518+02		Venv check		Found existing venv\n	0	268e2c16-5326-4898-82a6-65ee4494f6e6
596a05e6-8a78-48c0-85d4-259e79204a5a	2025-10-15 13:47:33.942864+02	2025-10-15 13:47:35.14581+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {} --export-compile-data --export-compile-data-file /tmp/tmpqgnldem9 --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.007 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.012 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.015 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.010 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Uploading 2 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 1 files are new and need to be uploaded\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/file/a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       DEBUG   Uploaded file with hash a94a8fe5ccb19ba61c4c0873d391e987982fbbd3\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=3 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test_orphan],v=3 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=3 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 3\nexporter       DEBUG   Committing resources took 0.017 seconds\ncompiler       DEBUG   The entire export command took 0.120 seconds\n	0	268e2c16-5326-4898-82a6-65ee4494f6e6
03b3fc52-a3ca-42e4-92c4-08e6af6fd0f3	2025-10-15 13:47:36.780408+02	2025-10-15 13:47:36.781234+02		Init		Using extra environment variables during compile \n	0	a80bb043-749a-49ef-9516-c62492dbe90e
7a0412ed-55cc-49f0-971e-c3a6c50ad8da	2025-10-15 13:47:36.781401+02	2025-10-15 13:47:36.781852+02		Venv check		Found existing venv\n	0	a80bb043-749a-49ef-9516-c62492dbe90e
3b80e2ab-2199-42e6-8378-c6ece72aef20	2025-10-15 13:47:35.339015+02	2025-10-15 13:47:36.677895+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpr9cmqr4m --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.009 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.014 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.013 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.009 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=4 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=4 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 4\nexporter       DEBUG   Committing resources took 0.033 seconds\ncompiler       DEBUG   The entire export command took 0.143 seconds\n	0	98c1dad8-4f4a-4b4e-b67c-b51801aca758
fc4e5d17-c200-4941-8413-c6e701809662	2025-10-15 13:47:38.062445+02	2025-10-15 13:47:38.374943+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core inmanta-license inmanta-support	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 17.0.0.dev0\nNot uninstalling inmanta-core at /home/hugo/work/inmanta/github-repos/inmanta-core/src, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\nFound existing installation: inmanta-license 5.0.0.dev20250528022222\nNot uninstalling inmanta-license at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-license'. No files were found to uninstall.\nFound existing installation: inmanta-support 5.0.0.dev20250528015607\nNot uninstalling inmanta-support at /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages, outside environment /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env\nCan't uninstall 'inmanta-support'. No files were found to uninstall.\n	0	540a4a72-9fca-457a-af8a-94d81c42a8a1
f0795f8d-8e1f-4b49-bb3a-72e92aae8b49	2025-10-15 13:47:36.782232+02	2025-10-15 13:47:37.957666+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp2vn2xb3z --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.007 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.012 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.011 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.007 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=5 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=5 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 5\nexporter       DEBUG   Committing resources took 0.015 seconds\ncompiler       DEBUG   The entire export command took 0.125 seconds\n	0	a80bb043-749a-49ef-9516-c62492dbe90e
ec5c964e-c687-4a4b-90da-9f960fd93a2f	2025-10-15 13:47:38.05968+02	2025-10-15 13:47:38.060458+02		Init		Using extra environment variables during compile \n	0	540a4a72-9fca-457a-af8a-94d81c42a8a1
6bad1ab8-7e1e-4d49-943c-6899370441bb	2025-10-15 13:47:38.060627+02	2025-10-15 13:47:38.061054+02		Venv check		Found existing venv\n	0	540a4a72-9fca-457a-af8a-94d81c42a8a1
bdfeede0-9024-4231-9af8-dae2e4607df1	2025-10-15 13:47:38.37602+02	2025-10-15 13:47:53.37292+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.module           DEBUG   Module versions before installation:\n                                 restbase: 2.4.3\n                                 fs: 1.1.1\n                                 mitogen: 0.2.4\n                                 std: 8.5.1\n                                 devtools: 0.2.0\n                                 netbox: 4.3.0\ninmanta.pip              DEBUG   Content of constraints files:\n                                     /tmp/tmpefj9bz1r:\n                                 Pip command: /tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m pip install --upgrade --upgrade-strategy eager -c /tmp/tmpefj9bz1r inmanta-module-fs inmanta-module-std inmanta-module-mitogen inmanta-module-std inmanta-license==5.0.0.dev20250528022222 inmanta-support==5.0.0.dev20250528015607 inmanta-core==17.0.0.dev0\ninmanta.pip              DEBUG   Looking in indexes: https://artifacts.internal.inmanta.com/inmanta/dev\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-fs in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-std in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (8.5.1)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-module-mitogen in ./.env/lib/python3.12/site-packages (0.2.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-license==5.0.0.dev20250528022222 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (5.0.0.dev20250528022222)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-support==5.0.0.dev20250528015607 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (5.0.0.dev20250528015607)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==17.0.0.dev0 in /home/hugo/work/inmanta/github-repos/inmanta-core/src (17.0.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: click<9,>=8.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (8.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (2.10.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (6.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<46,>=36 in ./.env/lib/python3.12/site-packages (from inmanta-license==5.0.0.dev20250528022222) (45.0.7)\ninmanta.pip              DEBUG   Requirement already satisfied: psutil<8,>=5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (7.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (6.5.2)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg~=0.25 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-support==5.0.0.dev20250528015607) (0.30.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.1.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (6.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.0.5)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.18,>=0.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: email-validator<3,>=1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2~=3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (3.1.6)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<11,>=8 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (10.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<25.1,>=21.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (25.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (25.2)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic!=2.9.2,~=2.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.12.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pynacl~=1.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.9.0.post0)\ninmanta.pip              DEBUG   Requirement already satisfied: setuptools in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (80.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.9 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.18.15)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: setproctitle~=1.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.3.7)\ninmanta.pip              DEBUG   Requirement already satisfied: SQLAlchemy~=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (2.0.44)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-sqlalchemy-mapper==0.7.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jsonpath-ng~=1.7 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from inmanta-core==17.0.0.dev0) (1.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: greenlet>=3.0.0rc1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (3.2.4)\ninmanta.pip              DEBUG   Requirement already satisfied: sentinel<1.1,>=0.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: sqlakeyset<3.0.0,>=2.0.1695177552 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (2.0.1746777265)\ninmanta.pip              DEBUG   Requirement already satisfied: strawberry-graphql>=0.236.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (0.283.3)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from build~=1.0->inmanta-core==17.0.0.dev0) (1.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (8.0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.32.5)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: rich in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (14.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.14 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cryptography<46,>=36->inmanta-license==5.0.0.dev20250528022222) (2.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=2.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from email-validator<3,>=1->inmanta-core==17.0.0.dev0) (2.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from email-validator<3,>=1->inmanta-core==17.0.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from jinja2~=3.0->inmanta-core==17.0.0.dev0) (3.0.3)\ninmanta.pip              DEBUG   Requirement already satisfied: annotated-types>=0.6.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (0.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic-core==2.41.4 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (2.41.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.14.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (4.15.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-inspection>=0.4.2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from pydantic!=2.9.2,~=2.5->inmanta-core==17.0.0.dev0) (0.4.2)\ninmanta.pip              DEBUG   Requirement already satisfied: six>=1.5 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from python-dateutil~=2.0->inmanta-core==17.0.0.dev0) (1.17.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.7 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from ruamel.yaml~=0.17->inmanta-core==17.0.0.dev0) (0.2.14)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from typing_inspect~=0.9->inmanta-core==17.0.0.dev0) (1.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: mitogen in ./.env/lib/python3.12/site-packages (from inmanta-module-mitogen) (0.3.29)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (5.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from cffi>=1.14->cryptography<46,>=36->inmanta-license==5.0.0.dev20250528022222) (2.23)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: charset_normalizer<4,>=2 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (3.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<3,>=1.21.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.5.0)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2025.10.5)\ninmanta.pip              DEBUG   Requirement already satisfied: graphql-core<3.4.0,>=3.2.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (3.2.6)\ninmanta.pip              DEBUG   Requirement already satisfied: lia-web>=0.2.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from strawberry-graphql>=0.236.0->strawberry-sqlalchemy-mapper==0.7.0->inmanta-core==17.0.0.dev0) (0.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: types-python-dateutil>=2.8.10 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from arrow->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.9.0.20251008)\ninmanta.pip              DEBUG   Requirement already satisfied: markdown-it-py>=2.2.0 in ./.env/lib/python3.12/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (4.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (2.19.2)\ninmanta.pip              DEBUG   Requirement already satisfied: mdurl~=0.1 in /home/hugo/.virtualenvs/core312/lib/python3.12/site-packages (from markdown-it-py>=2.2.0->rich->cookiecutter<3,>=1->inmanta-core==17.0.0.dev0) (0.1.2)\ninmanta.module           DEBUG   Successfully installed modules for project\n	0	540a4a72-9fca-457a-af8a-94d81c42a8a1
fe24fea5-10a3-47d9-b359-a1bff15ddcb6	2025-10-15 13:48:00.593304+02	2025-10-15 13:48:00.598523+02		Init		Using extra environment variables during compile \nFailed to compile: no project found in /tmp/tmpb776e72s/server/610b57e2-82b5-4559-9c48-e5890d2fc34e/compiler and no repository set.\n	1	c736b649-89eb-41e4-87e7-0c7cb5832614
a2eb7aca-f32d-4fe4-9386-de8b76685a32	2025-10-15 13:47:53.373667+02	2025-10-15 13:47:54.434804+02	/tmp/tmpb776e72s/server/7b2d2696-253e-4661-8d06-c887d7adadef/compiler/.env/bin/python -m inmanta.app -vvv export -X -e 7b2d2696-253e-4661-8d06-c887d7adadef --server_address localhost --server_port 47377 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpt8fepack --no-ssl	Recompiling configuration model	\n=================================== SUCCESS ===================================\n	compiler       INFO    Not setting up telemetry\ncompiler       DEBUG   Starting compile\ncompiler       DEBUG   Parsing took 0.006 seconds\ncompiler       DEBUG   Compiler cache observed 4 hits and 0 misses (100%)\ncompiler       DEBUG   Plugin loading took 0.011 seconds\ncompiler       INFO    The following modules are currently installed:\ncompiler       INFO    V2 modules:\ncompiler       INFO      fs: 1.1.1\ncompiler       INFO      mitogen: 0.2.4\ncompiler       INFO      std: 8.5.1\ncompiler       DEBUG   Found plugin std::unique_file(prefix: string, seed: string, suffix: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::template(path: string, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::generate_password(pw_id: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::password(pw_id: string) -> string\ncompiler       DEBUG   Found plugin std::print(message: Reference[any] | any) -> any\ncompiler       DEBUG   Found plugin std::replace(string: string, old: string, new: string) -> string\ncompiler       DEBUG   Found plugin std::equals(arg1: any, arg2: any, desc: string) -> any\ncompiler       DEBUG   Found plugin std::assert(expression: bool, message: string) -> any\ncompiler       DEBUG   Found plugin std::select(objects: list, attr: string) -> list\ncompiler       DEBUG   Found plugin std::item(objects: list, index: int) -> list\ncompiler       DEBUG   Found plugin std::key_sort(items: list, key: any) -> list\ncompiler       DEBUG   Found plugin std::timestamp(dummy: any) -> int\ncompiler       DEBUG   Found plugin std::capitalize(string: string) -> string\ncompiler       DEBUG   Found plugin std::upper(string: string) -> string\ncompiler       DEBUG   Found plugin std::lower(string: string) -> string\ncompiler       DEBUG   Found plugin std::limit(string: string, length: int) -> string\ncompiler       DEBUG   Found plugin std::type(obj: any) -> any\ncompiler       DEBUG   Found plugin std::sequence(i: int, start: int) -> list\ncompiler       DEBUG   Found plugin std::inlineif(conditional: bool, a: any, b: any) -> any\ncompiler       DEBUG   Found plugin std::at(objects: (Reference[any] | any)[], index: int) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::attr(obj: any, attr: string) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::isset(value: any) -> bool\ncompiler       DEBUG   Found plugin std::objid(value: any) -> string\ncompiler       DEBUG   Found plugin std::count(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::len(item_list: (Reference[any] | any)[]) -> int\ncompiler       DEBUG   Found plugin std::unique(item_list: list) -> bool\ncompiler       DEBUG   Found plugin std::flatten(item_list: list) -> list\ncompiler       DEBUG   Found plugin std::split(string_list: string, delim: string) -> list\ncompiler       DEBUG   Found plugin std::source(path: string) -> string\ncompiler       DEBUG   Found plugin std::file(path: string) -> string\ncompiler       DEBUG   Found plugin std::familyof(member: std::OS, family: string) -> bool\ncompiler       DEBUG   Found plugin std::getfact(resource: any, fact_name: string, default_value: any) -> any\ncompiler       DEBUG   Found plugin std::environment() -> string\ncompiler       DEBUG   Found plugin std::environment_name() -> string\ncompiler       DEBUG   Found plugin std::environment_server() -> string\ncompiler       DEBUG   Found plugin std::server_ca() -> string\ncompiler       DEBUG   Found plugin std::server_ssl() -> bool\ncompiler       DEBUG   Found plugin std::server_token(client_types: string[]) -> string\ncompiler       DEBUG   Found plugin std::server_port() -> int\ncompiler       DEBUG   Found plugin std::get_env(name: string, default_value: string?) -> string\ncompiler       DEBUG   Found plugin std::get_env_int(name: string, default_value: int?) -> int\ncompiler       DEBUG   Found plugin std::is_instance(obj: any, cls: string) -> bool\ncompiler       DEBUG   Found plugin std::length(value: string) -> int\ncompiler       DEBUG   Found plugin std::filter(values: list, not_item: std::Entity) -> list\ncompiler       DEBUG   Found plugin std::dict_get(dct: dict[string, any], key: string) -> string\ncompiler       DEBUG   Found plugin std::contains(dct: dict[string, any], key: string) -> bool\ncompiler       DEBUG   Found plugin std::getattr(entity: std::Entity, attribute_name: string, default_value: Reference[any] | any, no_unknown: bool) -> Reference[any] | any\ncompiler       DEBUG   Found plugin std::invert(value: bool) -> bool\ncompiler       DEBUG   Found plugin std::list_files(path: string) -> list\ncompiler       DEBUG   Found plugin std::is_unknown(value: Reference[any] | any) -> bool\ncompiler       DEBUG   Found plugin std::validate_type(fq_type_name: string, value: any, validation_parameters: dict[string, any]) -> bool\ncompiler       DEBUG   Found plugin std::is_base64_encoded(s: string) -> bool\ncompiler       DEBUG   Found plugin std::hostname(fqdn: string) -> string\ncompiler       DEBUG   Found plugin std::prefixlength_to_netmask(prefixlen: int) -> std::ipv4_address\ncompiler       DEBUG   Found plugin std::prefixlen(addr: std::ipv_any_interface) -> int\ncompiler       DEBUG   Found plugin std::network_address(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::netmask(addr: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ipindex(addr: std::ipv_any_network, position: int, keep_prefix: bool) -> string\ncompiler       DEBUG   Found plugin std::add_to_ip(addr: std::ipv_any_address, n: int) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::ip_address_from_interface(ip_interface: std::ipv_any_interface) -> std::ipv_any_address\ncompiler       DEBUG   Found plugin std::json_loads(s: string) -> any\ncompiler       DEBUG   Found plugin std::json_dumps(obj: any) -> string\ncompiler       DEBUG   Found plugin std::format(__string: string, *args: any, **kwargs: any) -> string\ncompiler       DEBUG   Found plugin std::create_int_reference(value: Reference[any] | any) -> Reference[int]\ncompiler       DEBUG   Found plugin std::create_environment_reference(name: Reference[string] | string) -> Reference[string]\ncompiler       DEBUG   Found plugin std::create_fact_reference(resource: std::Resource, fact_name: string) -> Reference[string]\ncompiler       DEBUG   Found plugin fs::source(path: string) -> string\ncompiler       DEBUG   Found plugin fs::file(path: string) -> string\ncompiler       DEBUG   Found plugin fs::list_files(path: string) -> list\ncompiler       DEBUG   Compilation took 0.010 seconds\ncompiler       DEBUG   Compile done\npy.warnings    WARNING /home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/compiler/__init__.py:259: PydanticDeprecatedSince20: The `json` method is deprecated; use `model_dump_json` instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/\n                         file.write("%s\\n" % self._data.export().json())\n\nexporter       DEBUG   Start transport for client compiler\nasyncio        DEBUG   Using selector: EpollSelector\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/reserve_version\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v2/protected_environment_settings\nexporter       DEBUG   Generating resources from the compiled model took 0.006 seconds\nexporter       INFO    Sending resources and handler source to server\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Uploading 1 files\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server POST http://localhost:47377/api/v1/file\nexporter       INFO    Only 0 files are new and need to be uploaded\nexporter       INFO    Sending resource updates to server\nexporter       DEBUG     std::AgentConfig[internal,agentname=localhost],v=6 not in any resource set\nexporter       DEBUG     fs::File[localhost,path=/tmp/test],v=6 not in any resource set\nasyncio        DEBUG   Using selector: EpollSelector\nexporter       DEBUG   Getting config in section compiler_rest_transport\nexporter       DEBUG   Calling server PUT http://localhost:47377/api/v1/version\nexporter       INFO    Committed resources with version 6\nexporter       DEBUG   Committing resources took 0.011 seconds\ncompiler       DEBUG   The entire export command took 0.098 seconds\n	0	540a4a72-9fca-457a-af8a-94d81c42a8a1
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, resource_id, agent, attributes, attribute_hash, resource_type, resource_id_value, is_undefined, resource_set) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	4c1627c7-2d20-4fa0-be2d-3e80870731a9
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	4c1627c7-2d20-4fa0-be2d-3e80870731a9
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	086de0b0-1f50-48ca-b120-cba7ca2f9cfb
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	086de0b0-1f50-48ca-b120-cba7ca2f9cfb
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	4d4a7634-5819-494b-87cd-55a16bf63ee2
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test_orphan]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3", "path": "/tmp/test_orphan", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	1ce12c233f61466dfa1e8f5230a76554	fs::File	/tmp/test_orphan	f	4d4a7634-5819-494b-87cd-55a16bf63ee2
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	4d4a7634-5819-494b-87cd-55a16bf63ee2
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	b1a0b081-efdf-4660-ae8f-334b25a1ee9f
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	b1a0b081-efdf-4660-ae8f-334b25a1ee9f
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	5ec4508e-1b9a-42a5-a2ce-b8a58d085fa4
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	5ec4508e-1b9a-42a5-a2ce-b8a58d085fa4
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	7727f465-2dff-4db1-b8cf-03b3a889747a
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	7727f465-2dff-4db1-b8cf-03b3a889747a
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	ac8bb22a-f214-43f4-bacf-e4a62fca6cc7
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	ac8bb22a-f214-43f4-bacf-e4a62fca6cc7
7b2d2696-253e-4661-8d06-c887d7adadef	test::Resource[agent3,key=key3]	agent3	{"key": "key2", "purged": false, "requires": [], "send_event": false}	15902cc7b9aabf14eb50594bc15db266	test::Resource	key3	f	e020cd24-ab42-4ad7-876f-c96d2f9564dd
7b2d2696-253e-4661-8d06-c887d7adadef	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	10b17baf-38fe-497a-8afa-65d6d1f934ee
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	localhost	{"via": {"name": "", "method_name": "local"}, "hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "mutators": [], "requires": ["std::AgentConfig[internal,agentname=localhost]"], "references": [], "send_event": true, "permissions": 644, "receive_events": true, "purge_on_delete": false}	ccbf282cc5a7ff0444045ccfc1cdd6d1	fs::File	/tmp/test	f	dd16f982-55a3-4def-bc9a-87b9bff45941
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	internal	{"uri": "local:", "purged": false, "mutators": [], "requires": [], "agentname": "localhost", "autostart": true, "references": [], "send_event": true, "receive_events": true, "purge_on_delete": false}	7b402b1da65696dee7b6da5f639df8ab	std::AgentConfig	localhost	f	dd16f982-55a3-4def-bc9a-87b9bff45941
7b2d2696-253e-4661-8d06-c887d7adadef	test::Resource[agent2,key=key2]	agent2	{"key": "key2", "purged": false, "requires": [], "send_event": false}	509af84c7d978674472e11ce2cad1b8b	test::Resource	key2	f	0c024707-2be7-4e92-b15f-03bf5c24b412
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key6]	agent1	{"key": "key6", "value": "val6", "purged": false, "requires": [], "send_event": true}	e0526e715e0780667151d80df5b87059	test::Resource	key6	f	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key1]	agent1	{"key": "key1", "value": "val1", "purged": false, "requires": [], "send_event": true}	84b23b0667021387d0c1651fae901e68	test::Resource	key1	f	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Fail[agent1,key=key2]	agent1	{"key": "key2", "value": "val2", "purged": false, "requires": [], "send_event": true}	fa7087083326c953261c388f13f3df3c	test::Fail	key2	f	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key3]	agent1	{"key": "key3", "value": "val3", "purged": false, "requires": ["test::Fail[agent1,key=key2]"], "send_event": true}	c455b56fd58fef5ebaa9bb23407c7776	test::Resource	key3	f	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key4]	agent1	{"key": "key4", "value": "val4", "purged": false, "requires": [], "send_event": true}	bb59a85a5232ca7dea81b07886770794	test::Resource	key4	t	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key5]	agent1	{"key": "key5", "value": "val5", "purged": false, "requires": ["test::Resource[agent1,key=key4]"], "send_event": true}	ec4c49c4764331f6a32c32375920547e	test::Resource	key5	f	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key7]	agent1	{"key": "key7", "value": "val7", "purged": false, "requires": [], "send_event": true}	d44ba2dab14d6d9d3897c96167c6e4f8	test::Resource	key7	f	57827dae-d283-41c8-8020-bd50fcdb4558
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key8]	agent1	{"key": "key8", "value": "val8", "purged": false, "requires": [], "send_event": true}	920faf6f55781fcff425670046dc957e	test::Resource	key8	f	57827dae-d283-41c8-8020-bd50fcdb4558
\.


--
-- Data for Name: resource_persistent_state; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_persistent_state (environment, resource_id, last_deploy, last_success, last_produced_events, last_deployed_attribute_hash, last_deployed_version, last_non_deploying_status, resource_type, agent, resource_id_value, current_intent_attribute_hash, is_undefined, is_orphan, last_deploy_result, blocked, is_deploying, created) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	test::Resource[agent3,key=key3]	2025-10-15 13:47:54.565944+02	\N	2025-10-15 13:47:54.565944+02	15902cc7b9aabf14eb50594bc15db266	7	unavailable	test::Resource	agent3	key3	15902cc7b9aabf14eb50594bc15db266	f	t	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:54.547592+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key6]	2025-10-15 13:47:55.019464+02	2025-10-15 13:47:55.014218+02	2025-10-15 13:47:55.019464+02	e0526e715e0780667151d80df5b87059	1	deployed	test::Resource	agent1	key6	e0526e715e0780667151d80df5b87059	f	t	DEPLOYED	NOT_BLOCKED	f	2025-10-15 13:47:55.004562+02
7b2d2696-253e-4661-8d06-c887d7adadef	test::Resource[agent2,key=key2]	2025-10-15 13:47:54.765127+02	\N	2025-10-15 13:47:54.765127+02	509af84c7d978674472e11ce2cad1b8b	8	unavailable	test::Resource	agent2	key2	509af84c7d978674472e11ce2cad1b8b	f	f	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:54.547592+02
7b2d2696-253e-4661-8d06-c887d7adadef	std::AgentConfig[internal,agentname=localhost]	2025-10-15 13:47:54.767755+02	\N	2025-10-15 13:47:54.767755+02	7b402b1da65696dee7b6da5f639df8ab	8	unavailable	std::AgentConfig	internal	localhost	7b402b1da65696dee7b6da5f639df8ab	f	f	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:32.645444+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key7]	2025-10-15 13:47:55.206958+02	2025-10-15 13:47:55.166122+02	2025-10-15 13:47:55.206958+02	d44ba2dab14d6d9d3897c96167c6e4f8	2	deployed	test::Resource	agent1	key7	d44ba2dab14d6d9d3897c96167c6e4f8	f	f	DEPLOYED	NOT_BLOCKED	f	2025-10-15 13:47:55.154841+02
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test]	2025-10-15 13:47:54.77287+02	\N	2025-10-15 13:47:54.77287+02	ccbf282cc5a7ff0444045ccfc1cdd6d1	8	unavailable	fs::File	localhost	/tmp/test	ccbf282cc5a7ff0444045ccfc1cdd6d1	f	f	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:32.645444+02
7b2d2696-253e-4661-8d06-c887d7adadef	fs::File[localhost,path=/tmp/test_orphan]	2025-10-15 13:47:35.232519+02	\N	2025-10-15 13:47:35.232519+02	1ce12c233f61466dfa1e8f5230a76554	3	unavailable	fs::File	localhost	/tmp/test_orphan	1ce12c233f61466dfa1e8f5230a76554	f	t	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:35.213315+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Fail[agent1,key=key2]	2025-10-15 13:47:55.216917+02	\N	2025-10-15 13:47:55.216917+02	fa7087083326c953261c388f13f3df3c	2	failed	test::Fail	agent1	key2	fa7087083326c953261c388f13f3df3c	f	f	FAILED	NOT_BLOCKED	f	2025-10-15 13:47:55.004562+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key5]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key5	ec4c49c4764331f6a32c32375920547e	f	f	NEW	BLOCKED	f	2025-10-15 13:47:55.004562+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key4]	\N	\N	\N	\N	\N	available	test::Resource	agent1	key4	bb59a85a5232ca7dea81b07886770794	t	f	NEW	BLOCKED	f	2025-10-15 13:47:55.004562+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key9]	2025-10-15 13:47:55.252055+02	2025-10-15 13:47:55.222214+02	2025-10-15 13:47:55.252055+02	a2101e55beec503a0c2501581a60b24e	2	deployed	test::Resource	agent1	key9	a2101e55beec503a0c2501581a60b24e	f	f	DEPLOYED	NOT_BLOCKED	f	2025-10-15 13:47:55.154841+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key1]	2025-10-15 13:47:55.025144+02	2025-10-15 13:47:55.020604+02	2025-10-15 13:47:55.025144+02	84b23b0667021387d0c1651fae901e68	1	deployed	test::Resource	agent1	key1	84b23b0667021387d0c1651fae901e68	f	f	DEPLOYED	NOT_BLOCKED	f	2025-10-15 13:47:55.004562+02
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	test::Resource[agent1,key=key3]	2025-10-15 13:47:55.029575+02	\N	2025-10-15 13:47:55.029575+02	c455b56fd58fef5ebaa9bb23407c7776	1	skipped	test::Resource	agent1	key3	c455b56fd58fef5ebaa9bb23407c7776	f	f	SKIPPED	NOT_BLOCKED	f	2025-10-15 13:47:55.004562+02
\.


--
-- Data for Name: resource_set; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set (environment, id, name) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	4c1627c7-2d20-4fa0-be2d-3e80870731a9	\N
7b2d2696-253e-4661-8d06-c887d7adadef	086de0b0-1f50-48ca-b120-cba7ca2f9cfb	\N
7b2d2696-253e-4661-8d06-c887d7adadef	4d4a7634-5819-494b-87cd-55a16bf63ee2	\N
7b2d2696-253e-4661-8d06-c887d7adadef	b1a0b081-efdf-4660-ae8f-334b25a1ee9f	\N
7b2d2696-253e-4661-8d06-c887d7adadef	5ec4508e-1b9a-42a5-a2ce-b8a58d085fa4	\N
7b2d2696-253e-4661-8d06-c887d7adadef	7727f465-2dff-4db1-b8cf-03b3a889747a	\N
7b2d2696-253e-4661-8d06-c887d7adadef	ac8bb22a-f214-43f4-bacf-e4a62fca6cc7	\N
7b2d2696-253e-4661-8d06-c887d7adadef	e020cd24-ab42-4ad7-876f-c96d2f9564dd	set-b
7b2d2696-253e-4661-8d06-c887d7adadef	10b17baf-38fe-497a-8afa-65d6d1f934ee	set-a
7b2d2696-253e-4661-8d06-c887d7adadef	dd16f982-55a3-4def-bc9a-87b9bff45941	\N
7b2d2696-253e-4661-8d06-c887d7adadef	0c024707-2be7-4e92-b15f-03bf5c24b412	set-a
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	56bb6431-5e6a-4f51-8999-a6457cd6972c	\N
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0af312bf-dc58-4aeb-bd09-884a2e1c01dc	\N
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	57827dae-d283-41c8-8020-bd50fcdb4558	\N
\.


--
-- Data for Name: resource_set_configuration_model; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource_set_configuration_model (environment, model, resource_set) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	1	4c1627c7-2d20-4fa0-be2d-3e80870731a9
7b2d2696-253e-4661-8d06-c887d7adadef	2	086de0b0-1f50-48ca-b120-cba7ca2f9cfb
7b2d2696-253e-4661-8d06-c887d7adadef	3	4d4a7634-5819-494b-87cd-55a16bf63ee2
7b2d2696-253e-4661-8d06-c887d7adadef	4	b1a0b081-efdf-4660-ae8f-334b25a1ee9f
7b2d2696-253e-4661-8d06-c887d7adadef	5	5ec4508e-1b9a-42a5-a2ce-b8a58d085fa4
7b2d2696-253e-4661-8d06-c887d7adadef	6	7727f465-2dff-4db1-b8cf-03b3a889747a
7b2d2696-253e-4661-8d06-c887d7adadef	7	ac8bb22a-f214-43f4-bacf-e4a62fca6cc7
7b2d2696-253e-4661-8d06-c887d7adadef	7	e020cd24-ab42-4ad7-876f-c96d2f9564dd
7b2d2696-253e-4661-8d06-c887d7adadef	7	10b17baf-38fe-497a-8afa-65d6d1f934ee
7b2d2696-253e-4661-8d06-c887d7adadef	8	dd16f982-55a3-4def-bc9a-87b9bff45941
7b2d2696-253e-4661-8d06-c887d7adadef	8	0c024707-2be7-4e92-b15f-03bf5c24b412
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	56bb6431-5e6a-4f51-8999-a6457cd6972c
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2	0af312bf-dc58-4aeb-bd09-884a2e1c01dc
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	3	57827dae-d283-41c8-8020-bd50fcdb4558
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
78c7b1fa-8f61-4605-984f-7edc739367d7	store	2025-10-15 13:47:32.395263+02	2025-10-15 13:47:32.402731+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2025-10-15T13:47:32.402742+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	1	{"std::AgentConfig[internal,agentname=localhost],v=1","fs::File[localhost,path=/tmp/test],v=1"}
11675fc0-503f-4dbe-97b8-f4fa3d8b6f4e	deploy	2025-10-15 13:47:32.652825+02	2025-10-15 13:47:32.661642+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=1: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\"}, \\"timestamp\\": \\"2025-10-15T13:47:32.661044+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
00e2e936-44ea-4307-ac2d-0d6cd2deedd9	deploy	2025-10-15 13:47:32.666112+02	2025-10-15 13:47:32.667403+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=1: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=1\\"}, \\"timestamp\\": \\"2025-10-15T13:47:32.667053+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	1	{"fs::File[localhost,path=/tmp/test],v=1"}
9971b77b-6949-4139-921d-6fb4763dac8a	store	2025-10-15 13:47:33.59607+02	2025-10-15 13:47:33.603+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2025-10-15T13:47:33.603010+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	2	{"std::AgentConfig[internal,agentname=localhost],v=2","fs::File[localhost,path=/tmp/test],v=2"}
7c818b57-a4fb-4af5-818a-516c3d44767d	store	2025-10-15 13:47:34.85971+02	2025-10-15 13:47:34.86256+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2025-10-15T13:47:34.862571+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	3	{"fs::File[localhost,path=/tmp/test],v=3","fs::File[localhost,path=/tmp/test_orphan],v=3","std::AgentConfig[internal,agentname=localhost],v=3"}
b07f6d7f-0802-4d95-8910-cd224140b002	deploy	2025-10-15 13:47:35.218135+02	2025-10-15 13:47:35.220615+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=3: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=3\\"}, \\"timestamp\\": \\"2025-10-15T13:47:35.220195+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	3	{"std::AgentConfig[internal,agentname=localhost],v=3"}
1dbe40ee-7c31-4afb-8971-3dd21e7b7ce5	deploy	2025-10-15 13:47:35.227523+02	2025-10-15 13:47:35.230252+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=3\\"}, \\"timestamp\\": \\"2025-10-15T13:47:35.229819+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	3	{"fs::File[localhost,path=/tmp/test],v=3"}
428bb43d-038b-41d1-a775-05f7877f09dd	deploy	2025-10-15 13:47:35.231422+02	2025-10-15 13:47:35.232519+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test_orphan],v=3: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test_orphan],v=3\\"}, \\"timestamp\\": \\"2025-10-15T13:47:35.232175+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	3	{"fs::File[localhost,path=/tmp/test_orphan],v=3"}
934de9e3-026e-4e7a-adc2-bf5930a7f193	store	2025-10-15 13:47:36.290216+02	2025-10-15 13:47:36.30103+02	{"{\\"msg\\": \\"Successfully stored version 4\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 4}, \\"timestamp\\": \\"2025-10-15T13:47:36.301056+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	4	{"fs::File[localhost,path=/tmp/test],v=4","std::AgentConfig[internal,agentname=localhost],v=4"}
c429a5fb-d8ff-48f3-8d1d-fa680af5bf01	deploy	2025-10-15 13:47:36.72578+02	2025-10-15 13:47:36.730792+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=4: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=4\\"}, \\"timestamp\\": \\"2025-10-15T13:47:36.730349+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	4	{"std::AgentConfig[internal,agentname=localhost],v=4"}
e387466f-d616-493a-83be-28bce1e8ca62	deploy	2025-10-15 13:47:36.732682+02	2025-10-15 13:47:36.736084+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=4: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=4\\"}, \\"timestamp\\": \\"2025-10-15T13:47:36.735701+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	4	{"fs::File[localhost,path=/tmp/test],v=4"}
b4bf0898-2818-4246-b559-53d800ed6013	store	2025-10-15 13:47:37.684112+02	2025-10-15 13:47:37.686552+02	{"{\\"msg\\": \\"Successfully stored version 5\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 5}, \\"timestamp\\": \\"2025-10-15T13:47:37.686560+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	5	{"fs::File[localhost,path=/tmp/test],v=5","std::AgentConfig[internal,agentname=localhost],v=5"}
264ec355-2a93-4b47-928f-09a90ed07908	store	2025-10-15 13:47:54.220502+02	2025-10-15 13:47:54.222398+02	{"{\\"msg\\": \\"Successfully stored version 6\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 6}, \\"timestamp\\": \\"2025-10-15T13:47:54.222405+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	6	{"std::AgentConfig[internal,agentname=localhost],v=6","fs::File[localhost,path=/tmp/test],v=6"}
27b0d587-980c-4f80-8808-f4b0e4b5ee78	store	2025-10-15 13:47:54.517943+02	2025-10-15 13:47:54.52181+02	{"{\\"msg\\": \\"Successfully stored version 7\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 7}, \\"timestamp\\": \\"2025-10-15T13:47:54.521817+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	7	{"test::Resource[agent2,key=key2],v=7","test::Resource[agent3,key=key3],v=7","std::AgentConfig[internal,agentname=localhost],v=7","fs::File[localhost,path=/tmp/test],v=7"}
7c352e5d-9191-44cc-9174-db6da61a7a75	deploy	2025-10-15 13:47:54.551651+02	2025-10-15 13:47:54.562784+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=7: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=7\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.562403+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	7	{"std::AgentConfig[internal,agentname=localhost],v=7"}
e11fdd1f-358a-4dd3-a422-a01b8df067ec	deploy	2025-10-15 13:47:54.570323+02	2025-10-15 13:47:54.571481+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=7: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=7\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.571048+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	7	{"fs::File[localhost,path=/tmp/test],v=7"}
699e1ac2-317a-4257-9ab1-1afe596badb9	deploy	2025-10-15 13:47:54.564419+02	2025-10-15 13:47:54.565944+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent3,key=key3],v=7: Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent3,key=key3],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent3,key=key3],v=7\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.565443+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	7	{"test::Resource[agent3,key=key3],v=7"}
8dab2b62-d23c-4818-8307-01d079452679	deploy	2025-10-15 13:47:54.562922+02	2025-10-15 13:47:54.564331+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=7: Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=7 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=7\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.563969+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	7	{"test::Resource[agent2,key=key2],v=7"}
49c2698f-c6a4-4e3e-89d3-2c84dd591f3c	store	2025-10-15 13:47:54.698328+02	2025-10-15 13:47:54.724996+02	{"{\\"msg\\": \\"Successfully stored version 8\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 8}, \\"timestamp\\": \\"2025-10-15T13:47:54.725007+02:00\\"}"}	\N	\N	\N	7b2d2696-253e-4661-8d06-c887d7adadef	8	{"std::AgentConfig[internal,agentname=localhost],v=8","fs::File[localhost,path=/tmp/test],v=8","test::Resource[agent2,key=key2],v=8"}
2aa74897-dd14-46dd-841e-df37db1c9c3f	deploy	2025-10-15 13:47:54.762791+02	2025-10-15 13:47:54.765127+02	{"{\\"msg\\": \\"Unable to deserialize test::Resource[agent2,key=key2],v=8: Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"Resource with id test::Resource[agent2,key=key2],v=8 does not have field value\\", \\"resource_id\\": \\"test::Resource[agent2,key=key2],v=8\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.764611+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	8	{"test::Resource[agent2,key=key2],v=8"}
ed137d58-5c25-4358-9cc8-bbc31c2efa70	deploy	2025-10-15 13:47:54.765246+02	2025-10-15 13:47:54.767755+02	{"{\\"msg\\": \\"Unable to deserialize std::AgentConfig[internal,agentname=localhost],v=8: No resource class registered for entity std::AgentConfig\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity std::AgentConfig\\", \\"resource_id\\": \\"std::AgentConfig[internal,agentname=localhost],v=8\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.767346+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	8	{"std::AgentConfig[internal,agentname=localhost],v=8"}
85e92c83-ee7f-4910-a6bb-59dbc132429f	deploy	2025-10-15 13:47:54.770425+02	2025-10-15 13:47:54.77287+02	{"{\\"msg\\": \\"Unable to deserialize fs::File[localhost,path=/tmp/test],v=8: No resource class registered for entity fs::File\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"cause\\": \\"No resource class registered for entity fs::File\\", \\"resource_id\\": \\"fs::File[localhost,path=/tmp/test],v=8\\"}, \\"timestamp\\": \\"2025-10-15T13:47:54.772486+02:00\\"}"}	unavailable	\N	nochange	7b2d2696-253e-4661-8d06-c887d7adadef	8	{"fs::File[localhost,path=/tmp/test],v=8"}
0012e1a8-1b53-436e-8e10-37b7141648e6	store	2025-10-15 13:47:54.996409+02	2025-10-15 13:47:55.002018+02	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2025-10-15T13:47:55.002025+02:00\\"}"}	\N	\N	\N	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	{"test::Fail[agent1,key=key2],v=1","test::Resource[agent1,key=key5],v=1","test::Resource[agent1,key=key4],v=1","test::Resource[agent1,key=key1],v=1","test::Resource[agent1,key=key6],v=1","test::Resource[agent1,key=key3],v=1"}
1b7f274d-bf34-49f2-b8a5-a28907e564ee	deploy	2025-10-15 13:47:55.014307+02	2025-10-15 13:47:55.019464+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key6\\"}, \\"deploy_id\\": \\"a0649194-c05a-48d8-a675-191b18ad5b8a\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.015849+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key6],v=1 in deploy a0649194-c05a-48d8-a675-191b18ad5b8a\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key6],v=1\\", \\"deploy_id\\": \\"a0649194-c05a-48d8-a675-191b18ad5b8a\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.019388+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key6],v=1": {"value": {"current": null, "desired": "val6"}}}	created	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	{"test::Resource[agent1,key=key6],v=1"}
45061d27-f3e6-45bb-85e7-f95d7f467b5a	deploy	2025-10-15 13:47:55.020686+02	2025-10-15 13:47:55.025144+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key1\\"}, \\"deploy_id\\": \\"e8b3e295-6d9d-4c77-851c-eda6f6f44b82\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.021320+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key1],v=1 in deploy e8b3e295-6d9d-4c77-851c-eda6f6f44b82\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key1],v=1\\", \\"deploy_id\\": \\"e8b3e295-6d9d-4c77-851c-eda6f6f44b82\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.025072+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key1],v=1": {"value": {"current": null, "desired": "val1"}}}	created	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	{"test::Resource[agent1,key=key1],v=1"}
ad26b680-8715-4210-8a86-3eee88fd639f	deploy	2025-10-15 13:47:55.026183+02	2025-10-15 13:47:55.027733+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"9e8f39c8-59f7-49e6-9e77-4ea47aab1556\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.026834+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of {'entity_type': 'test::Fail', 'agent_name': 'agent1', 'attribute': 'key', 'attribute_value': 'key2', 'version': 1} (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 884, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2615, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}}, \\"timestamp\\": \\"2025-10-15T13:47:55.027280+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=1 in deploy 9e8f39c8-59f7-49e6-9e77-4ea47aab1556\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=1\\", \\"deploy_id\\": \\"9e8f39c8-59f7-49e6-9e77-4ea47aab1556\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.027673+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=1": {"value": {"current": null, "desired": "val2"}}}	nochange	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	{"test::Fail[agent1,key=key2],v=1"}
cba73ce9-4bec-4897-a16f-ac962f481268	deploy	2025-10-15 13:47:55.028607+02	2025-10-15 13:47:55.029575+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 1, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key3\\"}, \\"deploy_id\\": \\"290684bb-e19f-45fb-9ae9-91ec7837347f\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.029269+02:00\\"}","{\\"msg\\": \\"Resource test::Resource[agent1,key=key3],v=1 skipped due to failed dependencies: ['test::Fail[agent1,key=key2]']\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"failed\\": \\"['test::Fail[agent1,key=key2]']\\", \\"resource\\": \\"test::Resource[agent1,key=key3],v=1\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.029397+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key3],v=1 in deploy 290684bb-e19f-45fb-9ae9-91ec7837347f\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key3],v=1\\", \\"deploy_id\\": \\"290684bb-e19f-45fb-9ae9-91ec7837347f\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.029508+02:00\\"}"}	skipped	\N	nochange	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1	{"test::Resource[agent1,key=key3],v=1"}
2efa47c5-c927-4b30-a745-b063012233a4	store	2025-10-15 13:47:55.132435+02	2025-10-15 13:47:55.14132+02	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2025-10-15T13:47:55.141355+02:00\\"}"}	\N	\N	\N	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2	{"test::Resource[agent1,key=key7],v=2","test::Resource[agent1,key=key5],v=2","test::Fail[agent1,key=key2],v=2","test::Resource[agent1,key=key1],v=2","test::Resource[agent1,key=key3],v=2","test::Resource[agent1,key=key9],v=2","test::Resource[agent1,key=key4],v=2"}
4b249325-293b-4770-ad7d-a057423bf2fc	deploy	2025-10-15 13:47:55.166322+02	2025-10-15 13:47:55.206958+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key7\\"}, \\"deploy_id\\": \\"9667bbf4-5d6c-4b6b-a9ec-8337765f4732\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.175540+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key7],v=2 in deploy 9667bbf4-5d6c-4b6b-a9ec-8337765f4732\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key7],v=2\\", \\"deploy_id\\": \\"9667bbf4-5d6c-4b6b-a9ec-8337765f4732\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.206706+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key7],v=2": {"value": {"current": null, "desired": "val7"}}}	created	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2	{"test::Resource[agent1,key=key7],v=2"}
915d6acd-ed0a-4c1a-b8cc-d10e3a52818b	deploy	2025-10-15 13:47:55.212537+02	2025-10-15 13:47:55.216917+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}, \\"deploy_id\\": \\"f9440e30-f6a7-4a4c-9eca-f7cd5b22895c\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.213983+02:00\\"}","{\\"msg\\": \\"An error occurred during deployment of {'entity_type': 'test::Fail', 'agent_name': 'agent1', 'attribute': 'key', 'attribute_value': 'key2', 'version': 2} (exception: Exception(''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exception\\": \\"Exception('')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 884, in execute\\\\n    self.do_changes(ctx, resource, changes)\\\\n  File \\\\\\"/home/hugo/work/inmanta/github-repos/inmanta-core/tests/conftest.py\\\\\\", line 2615, in do_changes\\\\n    raise Exception()\\\\nException\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Fail\\", \\"attribute_value\\": \\"key2\\"}}, \\"timestamp\\": \\"2025-10-15T13:47:55.214831+02:00\\"}","{\\"msg\\": \\"End run for resource test::Fail[agent1,key=key2],v=2 in deploy f9440e30-f6a7-4a4c-9eca-f7cd5b22895c\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Fail[agent1,key=key2],v=2\\", \\"deploy_id\\": \\"f9440e30-f6a7-4a4c-9eca-f7cd5b22895c\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.216750+02:00\\"}"}	failed	{"test::Fail[agent1,key=key2],v=2": {"value": {"current": null, "desired": "val2"}}}	nochange	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2	{"test::Fail[agent1,key=key2],v=2"}
99165214-8481-4855-b037-6fc8e87a3432	deploy	2025-10-15 13:47:55.222432+02	2025-10-15 13:47:55.252055+02	{"{\\"msg\\": \\"Start run because a new version was released.\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"reason\\": \\"a new version was released\\", \\"resource\\": {\\"version\\": 2, \\"attribute\\": \\"key\\", \\"agent_name\\": \\"agent1\\", \\"entity_type\\": \\"test::Resource\\", \\"attribute_value\\": \\"key9\\"}, \\"deploy_id\\": \\"bb463618-1f48-4b89-b45b-9b0164d93efa\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.225396+02:00\\"}","{\\"msg\\": \\"End run for resource test::Resource[agent1,key=key9],v=2 in deploy bb463618-1f48-4b89-b45b-9b0164d93efa\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"r_id\\": \\"test::Resource[agent1,key=key9],v=2\\", \\"deploy_id\\": \\"bb463618-1f48-4b89-b45b-9b0164d93efa\\"}, \\"timestamp\\": \\"2025-10-15T13:47:55.251801+02:00\\"}"}	deployed	{"test::Resource[agent1,key=key9],v=2": {"value": {"current": null, "desired": "val9"}}}	created	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2	{"test::Resource[agent1,key=key9],v=2"}
8f7526dd-0667-478f-ba3a-cc1f467fb48a	store	2025-10-15 13:48:00.399365+02	2025-10-15 13:48:00.419499+02	{"{\\"msg\\": \\"Successfully stored version 3\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 3}, \\"timestamp\\": \\"2025-10-15T13:48:00.419525+02:00\\"}"}	\N	\N	\N	9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	3	{"test::Resource[agent1,key=key4],v=3","test::Fail[agent1,key=key2],v=3","test::Resource[agent1,key=key1],v=3","test::Resource[agent1,key=key8],v=3","test::Resource[agent1,key=key3],v=3","test::Resource[agent1,key=key5],v=3","test::Resource[agent1,key=key7],v=3"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
7b2d2696-253e-4661-8d06-c887d7adadef	78c7b1fa-8f61-4605-984f-7edc739367d7	std::AgentConfig[internal,agentname=localhost]	1
7b2d2696-253e-4661-8d06-c887d7adadef	78c7b1fa-8f61-4605-984f-7edc739367d7	fs::File[localhost,path=/tmp/test]	1
7b2d2696-253e-4661-8d06-c887d7adadef	11675fc0-503f-4dbe-97b8-f4fa3d8b6f4e	std::AgentConfig[internal,agentname=localhost]	1
7b2d2696-253e-4661-8d06-c887d7adadef	00e2e936-44ea-4307-ac2d-0d6cd2deedd9	fs::File[localhost,path=/tmp/test]	1
7b2d2696-253e-4661-8d06-c887d7adadef	9971b77b-6949-4139-921d-6fb4763dac8a	std::AgentConfig[internal,agentname=localhost]	2
7b2d2696-253e-4661-8d06-c887d7adadef	9971b77b-6949-4139-921d-6fb4763dac8a	fs::File[localhost,path=/tmp/test]	2
7b2d2696-253e-4661-8d06-c887d7adadef	7c818b57-a4fb-4af5-818a-516c3d44767d	fs::File[localhost,path=/tmp/test]	3
7b2d2696-253e-4661-8d06-c887d7adadef	7c818b57-a4fb-4af5-818a-516c3d44767d	fs::File[localhost,path=/tmp/test_orphan]	3
7b2d2696-253e-4661-8d06-c887d7adadef	7c818b57-a4fb-4af5-818a-516c3d44767d	std::AgentConfig[internal,agentname=localhost]	3
7b2d2696-253e-4661-8d06-c887d7adadef	b07f6d7f-0802-4d95-8910-cd224140b002	std::AgentConfig[internal,agentname=localhost]	3
7b2d2696-253e-4661-8d06-c887d7adadef	1dbe40ee-7c31-4afb-8971-3dd21e7b7ce5	fs::File[localhost,path=/tmp/test]	3
7b2d2696-253e-4661-8d06-c887d7adadef	428bb43d-038b-41d1-a775-05f7877f09dd	fs::File[localhost,path=/tmp/test_orphan]	3
7b2d2696-253e-4661-8d06-c887d7adadef	934de9e3-026e-4e7a-adc2-bf5930a7f193	fs::File[localhost,path=/tmp/test]	4
7b2d2696-253e-4661-8d06-c887d7adadef	934de9e3-026e-4e7a-adc2-bf5930a7f193	std::AgentConfig[internal,agentname=localhost]	4
7b2d2696-253e-4661-8d06-c887d7adadef	c429a5fb-d8ff-48f3-8d1d-fa680af5bf01	std::AgentConfig[internal,agentname=localhost]	4
7b2d2696-253e-4661-8d06-c887d7adadef	e387466f-d616-493a-83be-28bce1e8ca62	fs::File[localhost,path=/tmp/test]	4
7b2d2696-253e-4661-8d06-c887d7adadef	b4bf0898-2818-4246-b559-53d800ed6013	fs::File[localhost,path=/tmp/test]	5
7b2d2696-253e-4661-8d06-c887d7adadef	b4bf0898-2818-4246-b559-53d800ed6013	std::AgentConfig[internal,agentname=localhost]	5
7b2d2696-253e-4661-8d06-c887d7adadef	264ec355-2a93-4b47-928f-09a90ed07908	std::AgentConfig[internal,agentname=localhost]	6
7b2d2696-253e-4661-8d06-c887d7adadef	264ec355-2a93-4b47-928f-09a90ed07908	fs::File[localhost,path=/tmp/test]	6
7b2d2696-253e-4661-8d06-c887d7adadef	27b0d587-980c-4f80-8808-f4b0e4b5ee78	test::Resource[agent2,key=key2]	7
7b2d2696-253e-4661-8d06-c887d7adadef	27b0d587-980c-4f80-8808-f4b0e4b5ee78	test::Resource[agent3,key=key3]	7
7b2d2696-253e-4661-8d06-c887d7adadef	27b0d587-980c-4f80-8808-f4b0e4b5ee78	std::AgentConfig[internal,agentname=localhost]	7
7b2d2696-253e-4661-8d06-c887d7adadef	27b0d587-980c-4f80-8808-f4b0e4b5ee78	fs::File[localhost,path=/tmp/test]	7
7b2d2696-253e-4661-8d06-c887d7adadef	7c352e5d-9191-44cc-9174-db6da61a7a75	std::AgentConfig[internal,agentname=localhost]	7
7b2d2696-253e-4661-8d06-c887d7adadef	8dab2b62-d23c-4818-8307-01d079452679	test::Resource[agent2,key=key2]	7
7b2d2696-253e-4661-8d06-c887d7adadef	699e1ac2-317a-4257-9ab1-1afe596badb9	test::Resource[agent3,key=key3]	7
7b2d2696-253e-4661-8d06-c887d7adadef	e11fdd1f-358a-4dd3-a422-a01b8df067ec	fs::File[localhost,path=/tmp/test]	7
7b2d2696-253e-4661-8d06-c887d7adadef	49c2698f-c6a4-4e3e-89d3-2c84dd591f3c	std::AgentConfig[internal,agentname=localhost]	8
7b2d2696-253e-4661-8d06-c887d7adadef	49c2698f-c6a4-4e3e-89d3-2c84dd591f3c	fs::File[localhost,path=/tmp/test]	8
7b2d2696-253e-4661-8d06-c887d7adadef	49c2698f-c6a4-4e3e-89d3-2c84dd591f3c	test::Resource[agent2,key=key2]	8
7b2d2696-253e-4661-8d06-c887d7adadef	2aa74897-dd14-46dd-841e-df37db1c9c3f	test::Resource[agent2,key=key2]	8
7b2d2696-253e-4661-8d06-c887d7adadef	ed137d58-5c25-4358-9cc8-bbc31c2efa70	std::AgentConfig[internal,agentname=localhost]	8
7b2d2696-253e-4661-8d06-c887d7adadef	85e92c83-ee7f-4910-a6bb-59dbc132429f	fs::File[localhost,path=/tmp/test]	8
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Fail[agent1,key=key2]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Resource[agent1,key=key5]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Resource[agent1,key=key4]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Resource[agent1,key=key1]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Resource[agent1,key=key6]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	0012e1a8-1b53-436e-8e10-37b7141648e6	test::Resource[agent1,key=key3]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	1b7f274d-bf34-49f2-b8a5-a28907e564ee	test::Resource[agent1,key=key6]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	45061d27-f3e6-45bb-85e7-f95d7f467b5a	test::Resource[agent1,key=key1]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	ad26b680-8715-4210-8a86-3eee88fd639f	test::Fail[agent1,key=key2]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	cba73ce9-4bec-4897-a16f-ac962f481268	test::Resource[agent1,key=key3]	1
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key7]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key5]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Fail[agent1,key=key2]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key1]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key3]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key9]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2efa47c5-c927-4b30-a745-b063012233a4	test::Resource[agent1,key=key4]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	4b249325-293b-4770-ad7d-a057423bf2fc	test::Resource[agent1,key=key7]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	915d6acd-ed0a-4c1a-b8cc-d10e3a52818b	test::Fail[agent1,key=key2]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	99165214-8481-4855-b037-6fc8e87a3432	test::Resource[agent1,key=key9]	2
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key4]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Fail[agent1,key=key2]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key1]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key8]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key3]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key5]	3
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	8f7526dd-0667-478f-ba3a-cc1f467fb48a	test::Resource[agent1,key=key7]	3
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
7b2d2696-253e-4661-8d06-c887d7adadef	8
9e1f1e79-200d-4d31-b13e-ac78eff2eb4f	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, installed_versions) FROM stdin;
core	{1,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190,202302200,202302270,202303070,202303071,202304060,202304070,202306060,202308010,202308020,202308100,202309120,202309130,202310040,202310090,202310180,202311170,202312190,202401160,202401260,202402080,202402130,202403010,202403110,202403120,202403210,202403220,202403280,202407290,202409090,202410310,202411140,202501140,202503030,202504040,202504220,202505090,202505150,202505260,202506160,202506250,202507030,202507080,202508040,202509050,202509090,202509100,202509110,202509180,202510150}
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
    ADD CONSTRAINT agent_modules_pkey PRIMARY KEY (environment, cm_version, agent_name, inmanta_module_name);


--
-- Name: agent agent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_pkey PRIMARY KEY (environment, name);


--
-- Name: agentinstance agentinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentinstance
    ADD CONSTRAINT agentinstance_pkey PRIMARY KEY (id);


--
-- Name: agentinstance agentinstance_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentinstance
    ADD CONSTRAINT agentinstance_unique UNIQUE (tid, process, name);


--
-- Name: agentprocess agentprocess_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentprocess
    ADD CONSTRAINT agentprocess_pkey PRIMARY KEY (sid);


--
-- Name: compile compile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compile
    ADD CONSTRAINT compile_pkey PRIMARY KEY (id);


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
-- Name: agent_id_primary_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_id_primary_index ON public.agent USING btree (id_primary);


--
-- Name: agent_modules_environment_agent_name_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_modules_environment_agent_name_index ON public.agent_modules USING btree (environment, agent_name);


--
-- Name: agent_modules_environment_module_name_module_version_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_modules_environment_module_name_module_version_index ON public.agent_modules USING btree (environment, inmanta_module_name, inmanta_module_version);


--
-- Name: agentinstance_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentinstance_expired_index ON public.agentinstance USING btree (expired) WHERE (expired IS NULL);


--
-- Name: agentinstance_expired_tid_endpoint_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentinstance_expired_tid_endpoint_index ON public.agentinstance USING btree (tid, name, expired);


--
-- Name: agentinstance_process_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentinstance_process_index ON public.agentinstance USING btree (process);


--
-- Name: agentprocess_env_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentprocess_env_expired_index ON public.agentprocess USING btree (environment, expired);


--
-- Name: agentprocess_env_hostname_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentprocess_env_hostname_expired_index ON public.agentprocess USING btree (environment, hostname, expired);


--
-- Name: agentprocess_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agentprocess_expired_index ON public.agentprocess USING btree (expired) WHERE (expired IS NULL);


--
-- Name: agentprocess_sid_expired_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX agentprocess_sid_expired_index ON public.agentprocess USING btree (sid, expired);


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
-- Name: resource_env_attr_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_attr_hash_index ON public.resource USING btree (environment, attribute_hash);


--
-- Name: resource_environment_agent_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_agent_idx ON public.resource USING btree (environment, agent);


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
-- Name: resource_persistent_state_environment_resource_id_is_orphan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_id_is_orphan ON public.resource_persistent_state USING btree (environment, resource_id, is_orphan);


--
-- Name: resource_persistent_state_environment_resource_id_value_res_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_id_value_res_idx ON public.resource_persistent_state USING btree (environment, resource_id_value, resource_id);


--
-- Name: resource_persistent_state_environment_resource_type_resourc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_persistent_state_environment_resource_type_resourc_idx ON public.resource_persistent_state USING btree (environment, resource_type, resource_id);


--
-- Name: resource_resource_id_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_resource_id_index ON public.resource USING btree (resource_id);


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
-- Name: agent agent_id_primary_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_id_primary_fkey FOREIGN KEY (id_primary) REFERENCES public.agentinstance(id) ON DELETE RESTRICT;


--
-- Name: agent_modules agent_modules_environment_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_agent_name_fkey FOREIGN KEY (environment, agent_name) REFERENCES public.agent(environment, name) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_environment_cm_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_cm_version_fkey FOREIGN KEY (environment, cm_version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: agent_modules agent_modules_environment_inmanta_module_name_inmanta_modu_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_modules
    ADD CONSTRAINT agent_modules_environment_inmanta_module_name_inmanta_modu_fkey FOREIGN KEY (environment, inmanta_module_name, inmanta_module_version) REFERENCES public.inmanta_module(environment, name, version) ON DELETE RESTRICT;


--
-- Name: agentinstance agentinstance_process_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentinstance
    ADD CONSTRAINT agentinstance_process_fkey FOREIGN KEY (process) REFERENCES public.agentprocess(sid) ON DELETE CASCADE;


--
-- Name: agentprocess agentprocess_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agentprocess
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
-- Name: resource_persistent_state resource_persistent_state_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource_persistent_state
    ADD CONSTRAINT resource_persistent_state_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


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

