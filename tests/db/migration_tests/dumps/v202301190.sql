--
-- PostgreSQL database dump
--

-- Dumped from database version 13.6
-- Dumped by pg_dump version 13.6

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
-- Name: code; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.code (
    environment uuid NOT NULL,
    resource character varying NOT NULL,
    version integer NOT NULL,
    source_refs jsonb
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
    environment_variables jsonb,
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
    exporter_plugin character varying
);


--
-- Name: configurationmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationmodel (
    version integer NOT NULL,
    environment uuid NOT NULL,
    date timestamp with time zone,
    released boolean DEFAULT false,
    deployed boolean DEFAULT false,
    result public.versionstate DEFAULT 'pending'::public.versionstate,
    version_info jsonb,
    total integer DEFAULT 0,
    undeployable character varying[],
    skipped_for_undeployable character varying[],
    partial_base integer
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
    icon character varying(65535) DEFAULT ''::character varying
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
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification (
    id uuid NOT NULL,
    environment uuid NOT NULL,
    created timestamp with time zone NOT NULL,
    title character varying NOT NULL,
    message character varying NOT NULL,
    severity public.notificationseverity DEFAULT 'message'::public.notificationseverity,
    uri character varying NOT NULL,
    read boolean DEFAULT false NOT NULL,
    cleared boolean DEFAULT false NOT NULL
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
    metadata jsonb
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
    model integer NOT NULL,
    resource_id character varying NOT NULL,
    agent character varying NOT NULL,
    last_deploy timestamp with time zone,
    attributes jsonb,
    attribute_hash character varying,
    status public.resourcestate DEFAULT 'available'::public.resourcestate,
    provides character varying[] DEFAULT ARRAY[]::character varying[],
    resource_type character varying NOT NULL,
    resource_id_value character varying NOT NULL,
    last_non_deploying_status public.non_deploying_resource_state DEFAULT 'available'::public.non_deploying_resource_state NOT NULL,
    resource_set character varying
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
-- Name: schemamanager; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schemamanager (
    name character varying NOT NULL,
    legacy_version integer,
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
f7d137a1-c720-4ff2-817c-9e9231e279ba	localhost	2023-01-19 14:31:00.175595+01	f	24207b83-1d11-42dd-b103-0d9fb7179fc3	\N
f7d137a1-c720-4ff2-817c-9e9231e279ba	internal	2023-01-19 14:31:01.663104+01	f	82212659-bab2-4324-92ea-e9c70cadb940	\N
\.


--
-- Data for Name: agentinstance; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentinstance (id, process, name, expired, tid) FROM stdin;
24207b83-1d11-42dd-b103-0d9fb7179fc3	832c9e96-97fd-11ed-8c2b-84144dfe5579	localhost	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba
82212659-bab2-4324-92ea-e9c70cadb940	832c9e96-97fd-11ed-8c2b-84144dfe5579	internal	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba
d42ac0bd-581f-4900-a9ca-e2261e5072ff	82d4592a-97fd-11ed-b0f9-84144dfe5579	internal	2023-01-19 14:31:01.663104+01	f7d137a1-c720-4ff2-817c-9e9231e279ba
\.


--
-- Data for Name: agentprocess; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentprocess (hostname, environment, first_seen, last_seen, expired, sid) FROM stdin;
arnaud-inmanta-laptop	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:30:59.597103+01	2023-01-19 14:30:59.66286+01	2023-01-19 14:31:01.663104+01	82d4592a-97fd-11ed-b0f9-84144dfe5579
arnaud-inmanta-laptop	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:31:00.175595+01	2023-01-19 14:31:09.040648+01	\N	832c9e96-97fd-11ed-8c2b-84144dfe5579
\.


--
-- Data for Name: code; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.code (environment, resource, version, source_refs) FROM stdin;
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Service	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::File	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Directory	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Package	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Symlink	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::AgentConfig	1	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Service	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::File	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Directory	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Package	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::Symlink	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
f7d137a1-c720-4ff2-817c-9e9231e279ba	std::AgentConfig	2	{"db0b95ee005147666e020669ad62de99f657791b": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/resources.py", "inmanta_plugins.std.resources", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]], "e13ad6e395f94b178f8627cbe0b8125d46e7abf0": ["/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std/plugins/__init__.py", "inmanta_plugins.std", ["Jinja2~=3.1", "email_validator~=1.3", "pydantic~=1.10", "dataclasses~=0.7;python_version<'3.7'"]]}
\.


--
-- Data for Name: compile; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.compile (id, environment, started, completed, requested, metadata, environment_variables, do_export, force_update, success, version, remote_id, handled, substitute_compile_id, compile_data, partial, removed_resource_sets, notify_failed_compile, failed_compile_message, exporter_plugin) FROM stdin;
ee3c3f74-5226-4046-a498-854205feea69	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:30:50.430684+01	2023-01-19 14:30:59.692322+01	2023-01-19 14:30:50.423237+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	1	e176214e-5c99-4579-bb37-0a0ed9bf6e9e	t	\N	{"errors": []}	f	{}	\N	\N	\N
e76953a2-7688-4e98-a38c-4a5adac3689c	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:31:00.275943+01	2023-01-19 14:31:09.092836+01	2023-01-19 14:31:00.270874+01	{"type": "api", "message": "Recompile trigger through API call"}	{}	t	t	t	2	56071825-be41-4a90-986a-6d37a4200e97	t	\N	{"errors": []}	f	{}	\N	\N	\N
\.


--
-- Data for Name: configurationmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.configurationmodel (version, environment, date, released, deployed, result, version_info, total, undeployable, skipped_for_undeployable, partial_base) FROM stdin;
1	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:30:59.183613+01	t	t	failed	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N
2	f7d137a1-c720-4ff2-817c-9e9231e279ba	2023-01-19 14:31:09.011881+01	t	t	deploying	{"export_metadata": {"type": "api", "message": "Recompile trigger through API call", "cli-user": "arnaud", "hostname": "arnaud-inmanta-laptop", "inmanta:compile:state": "success"}}	2	{}	{}	\N
\.


--
-- Data for Name: dryrun; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dryrun (id, environment, model, date, total, todo, resources) FROM stdin;
\.


--
-- Data for Name: environment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.environment (id, name, project, repo_url, repo_branch, settings, last_version, halted, description, icon) FROM stdin;
14bb6e05-0e4f-47be-981a-7649d7f9095b	dev-2	19d69e46-af80-4f37-910b-261e323c93d1			{"auto_full_compile": ""}	0	f		
f7d137a1-c720-4ff2-817c-9e9231e279ba	dev-1	19d69e46-af80-4f37-910b-261e323c93d1			{"auto_deploy": true, "server_compile": true, "purge_on_delete": false, "auto_full_compile": "", "recompile_backoff": 0.1, "autostart_agent_map": {"internal": "local:", "localhost": "local:"}, "push_on_auto_deploy": true, "autostart_agent_deploy_interval": 0, "autostart_agent_repair_interval": 600, "autostart_agent_deploy_splay_time": 0, "autostart_agent_repair_splay_time": 0, "agent_trigger_method_on_auto_deploy": "push_incremental_deploy"}	2	f		
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
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification (id, environment, created, title, message, severity, uri, read, cleared) FROM stdin;
\.


--
-- Data for Name: parameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.parameter (id, name, value, environment, resource_id, source, updated, metadata) FROM stdin;
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, name) FROM stdin;
19d69e46-af80-4f37-910b-261e323c93d1	project-test-a
\.


--
-- Data for Name: report; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.report (id, started, completed, command, name, errstream, outstream, returncode, compile) FROM stdin;
c81ee6b1-5e68-4e59-8d0f-dcc7fb593889	2023-01-19 14:30:50.430999+01	2023-01-19 14:30:50.432026+01		Init		Using extra environment variables during compile \n	0	ee3c3f74-5226-4046-a498-854205feea69
3d4c930e-d83a-4e06-87ee-5dc06f7c1acb	2023-01-19 14:30:50.432307+01	2023-01-19 14:30:50.433137+01		Creating venv			0	ee3c3f74-5226-4046-a498-854205feea69
cbf9d20f-539c-40ff-9b96-fd256a75b3a7	2023-01-19 14:31:00.276232+01	2023-01-19 14:31:00.277634+01		Init		Using extra environment variables during compile \n	0	e76953a2-7688-4e98-a38c-4a5adac3689c
ded349cd-3665-46c7-a455-99fc00481b1f	2023-01-19 14:30:50.436584+01	2023-01-19 14:30:50.689954+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.1.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	ee3c3f74-5226-4046-a498-854205feea69
0334e0b5-c84f-439d-a511-5a3d6f93c36a	2023-01-19 14:30:50.690958+01	2023-01-19 14:30:58.372537+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.module           DEBUG   Cloning into '/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std'...\ninmanta.module           DEBUG   Installing module std (v1) (with no version constraints).\ninmanta.module           INFO    Checking out 4.1.1 on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.module           DEBUG   Successfully installed module std (v1) version 4.1.1 in /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std from https://github.com/inmanta/std.\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000094 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 0 hits and 2 misses (0%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.module           INFO    Checking out 4.1.1 on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 pydantic~=1.10 Jinja2~=3.1 inmanta-core==8.1.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.1.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (6.1.2)\ninmanta.pip              DEBUG   Collecting python-slugify>=4.0.0\ninmanta.pip              DEBUG   Using cached python_slugify-7.0.0-py2.py3-none-any.whl (9.4 kB)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.1.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.1.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Installing collected packages: python-slugify\ninmanta.pip              DEBUG   Attempting uninstall: python-slugify\ninmanta.pip              DEBUG   Found existing installation: python-slugify 6.1.2\ninmanta.pip              DEBUG   Not uninstalling python-slugify at /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages, outside environment /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env\ninmanta.pip              DEBUG   Can't uninstall 'python-slugify'. No files were found to uninstall.\ninmanta.pip              DEBUG   ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.\ninmanta.pip              DEBUG   pyadr 0.19.0 requires python-slugify<7,>=6, but you have python-slugify 7.0.0 which is incompatible.\ninmanta.pip              DEBUG   Successfully installed python-slugify-7.0.0\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000055 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 1 hits and 2 misses (33%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.module           INFO    Checking out 4.1.1 on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip install --upgrade --upgrade-strategy eager dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 pydantic~=1.10 Jinja2~=3.1 inmanta-core==8.1.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.1.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.1.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.1.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\n	0	ee3c3f74-5226-4046-a498-854205feea69
6e8b8b07-b7d0-48fb-bbd3-16af2cbf427e	2023-01-19 14:30:58.373797+01	2023-01-19 14:30:59.691201+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m inmanta.app -vvv export -X -e f7d137a1-c720-4ff2-817c-9e9231e279ba --server_address localhost --server_port 55709 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmpk0819_i1 --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004115 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000091 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002474)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001660)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000234)\ninmanta.execute.schedulerINFO    Total compilation time 0.004514\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/file/db0b95ee005147666e020669ad62de99f657791b\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/file/e13ad6e395f94b178f8627cbe0b8125d46e7abf0\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/codebatched/1\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v1/file\ninmanta.export           INFO    Only 1 files are new and need to be uploaded\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/file/7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           DEBUG   Uploaded file with hash 7110eda4d09e062aa5e4a390b0a572ac0d2c0220\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=1\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=1\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/version\ninmanta.export           INFO    Committed resources with version 1\n	0	ee3c3f74-5226-4046-a498-854205feea69
c6759b84-3bf7-4437-978e-7885df2ad40c	2023-01-19 14:31:00.282489+01	2023-01-19 14:31:00.551174+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip uninstall -y inmanta inmanta-service-orchestrator inmanta-core	Uninstall inmanta packages from the compiler venv	WARNING: Skipping inmanta as it is not installed.\nWARNING: Skipping inmanta-service-orchestrator as it is not installed.\n	Found existing installation: inmanta-core 8.1.0.dev0\nNot uninstalling inmanta-core at /home/arnaud/Documents/projects/inmanta-core/src, outside environment /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env\nCan't uninstall 'inmanta-core'. No files were found to uninstall.\n	0	e76953a2-7688-4e98-a38c-4a5adac3689c
5c0393e5-ac1e-4fad-a712-5eebe5ba13b4	2023-01-19 14:31:00.552492+01	2023-01-19 14:31:08.233783+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m inmanta.app -vvv -X project update	Updating modules		inmanta.moduletool       INFO    Performing update attempt 1 of 5\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.000072 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.module           INFO    Checking out 4.1.1 on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 pydantic~=1.10 inmanta-core==8.1.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.1.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.1.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.1.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2022.12.7)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.26.14)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.moduletool       INFO    Performing update attempt 2 of 5\ninmanta.module           DEBUG   Parsing took 0.000054 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 3 hits and 0 misses (100%)\ninmanta.module           INFO    Performing fetch on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.module           INFO    Checking out 4.1.1 on /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/libs/std\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.pip              DEBUG   Pip command: /tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m pip install --upgrade --upgrade-strategy eager Jinja2~=3.1 dataclasses~=0.7; python_version < "3.7" email_validator~=1.3 pydantic~=1.10 inmanta-core==8.1.0.dev0\ninmanta.pip              DEBUG   Ignoring dataclasses: markers 'python_version < "3.7"' don't match your environment\ninmanta.pip              DEBUG   Requirement already satisfied: Jinja2~=3.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (3.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: email_validator~=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (1.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pydantic~=1.10 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (1.10.4)\ninmanta.pip              DEBUG   Requirement already satisfied: inmanta-core==8.1.0.dev0 in /home/arnaud/Documents/projects/inmanta-core/src (8.1.0.dev0)\ninmanta.pip              DEBUG   Requirement already satisfied: asyncpg<0.28,~=0.25 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.27.0)\ninmanta.pip              DEBUG   Requirement already satisfied: click-plugins~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: click<8.2,>=8.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (8.1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: colorlog~=6.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.7.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cookiecutter<3,>=1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.1.1)\ninmanta.pip              DEBUG   Requirement already satisfied: crontab<2.0,>=0.23 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: cryptography<40,>=36 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (39.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: docstring-parser<0.16,>=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.15)\ninmanta.pip              DEBUG   Requirement already satisfied: execnet~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.9.0)\ninmanta.pip              DEBUG   Requirement already satisfied: importlib_metadata<7,>=4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: more-itertools<10,>=8 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (9.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: netifaces~=0.11 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: packaging<24.0,>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (23.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pip>=21.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (22.3.1)\ninmanta.pip              DEBUG   Requirement already satisfied: ply~=3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (3.11)\ninmanta.pip              DEBUG   Requirement already satisfied: pyformance~=0.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.4)\ninmanta.pip              DEBUG   Requirement already satisfied: PyJWT~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: python-dateutil~=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (2.8.2)\ninmanta.pip              DEBUG   Requirement already satisfied: pyyaml~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.0)\ninmanta.pip              DEBUG   Requirement already satisfied: texttable~=1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (1.6.7)\ninmanta.pip              DEBUG   Requirement already satisfied: tornado~=6.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (6.2)\ninmanta.pip              DEBUG   Requirement already satisfied: typing_inspect~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.8.0)\ninmanta.pip              DEBUG   Requirement already satisfied: build~=0.7 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml~=0.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.17.21)\ninmanta.pip              DEBUG   Requirement already satisfied: toml~=0.10 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from inmanta-core==8.1.0.dev0) (0.10.2)\ninmanta.pip              DEBUG   Requirement already satisfied: MarkupSafe>=2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from Jinja2~=3.1) (2.1.2)\ninmanta.pip              DEBUG   Requirement already satisfied: dnspython>=1.15.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (2.3.0)\ninmanta.pip              DEBUG   Requirement already satisfied: idna>=2.0.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from email_validator~=1.3) (3.4)\ninmanta.pip              DEBUG   Requirement already satisfied: typing-extensions>=4.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pydantic~=1.10) (4.4.0)\ninmanta.pip              DEBUG   Requirement already satisfied: tomli>=1.1.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (2.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: pyproject_hooks in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from build~=0.7->inmanta-core==8.1.0.dev0) (1.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: jinja2-time>=0.2.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.2.0)\ninmanta.pip              DEBUG   Requirement already satisfied: requests>=2.23.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2.28.2)\ninmanta.pip              DEBUG   Requirement already satisfied: python-slugify>=4.0.0 in ./.env/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (7.0.0)\ninmanta.pip              DEBUG   Requirement already satisfied: binaryornot>=0.4.4 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (0.4.4)\ninmanta.pip              DEBUG   Requirement already satisfied: cffi>=1.12 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from cryptography<40,>=36->inmanta-core==8.1.0.dev0) (1.15.1)\ninmanta.pip              DEBUG   Requirement already satisfied: zipp>=0.5 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from importlib_metadata<7,>=4->inmanta-core==8.1.0.dev0) (3.11.0)\ninmanta.pip              DEBUG   Requirement already satisfied: six in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from pyformance~=0.4->inmanta-core==8.1.0.dev0) (1.16.0)\ninmanta.pip              DEBUG   Requirement already satisfied: ruamel.yaml.clib>=0.2.6 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from ruamel.yaml~=0.17->inmanta-core==8.1.0.dev0) (0.2.7)\ninmanta.pip              DEBUG   Requirement already satisfied: mypy-extensions>=0.3.0 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from typing_inspect~=0.7->inmanta-core==8.1.0.dev0) (0.4.3)\ninmanta.pip              DEBUG   Requirement already satisfied: chardet>=3.0.2 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from binaryornot>=0.4.4->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (5.1.0)\ninmanta.pip              DEBUG   Requirement already satisfied: pycparser in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from cffi>=1.12->cryptography<40,>=36->inmanta-core==8.1.0.dev0) (2.21)\ninmanta.pip              DEBUG   Requirement already satisfied: arrow in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from jinja2-time>=0.2.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.2.3)\ninmanta.pip              DEBUG   Requirement already satisfied: text-unidecode>=1.3 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from python-slugify>=4.0.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.3)\ninmanta.pip              DEBUG   Requirement already satisfied: urllib3<1.27,>=1.21.1 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (1.26.14)\ninmanta.pip              DEBUG   Requirement already satisfied: charset-normalizer<4,>=2 in /home/arnaud/.virtualenvs/inmanta-core/lib64/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (3.0.1)\ninmanta.pip              DEBUG   Requirement already satisfied: certifi>=2017.4.17 in /home/arnaud/.virtualenvs/inmanta-core/lib/python3.9/site-packages (from requests>=2.23.0->cookiecutter<3,>=1->inmanta-core==8.1.0.dev0) (2022.12.7)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\n	0	e76953a2-7688-4e98-a38c-4a5adac3689c
2b53a6ba-b306-4fe6-a8ca-b4d14a72a4e1	2023-01-19 14:31:08.235031+01	2023-01-19 14:31:09.091297+01	/tmp/tmp7itao176/server/environments/f7d137a1-c720-4ff2-817c-9e9231e279ba/.env/bin/python -m inmanta.app -vvv export -X -e f7d137a1-c720-4ff2-817c-9e9231e279ba --server_address localhost --server_port 55709 --metadata {"type": "api", "message": "Recompile trigger through API call"} --export-compile-data --export-compile-data-file /tmp/tmp71hroidk --no-ssl	Recompiling configuration model		inmanta.compiler         DEBUG   Starting compile\ninmanta.warnings         WARNING InmantaWarning: Loaded V1 module std. The use of V1 modules is deprecated. Use the equivalent V2 module instead.\ninmanta.module           DEBUG   Parsing took 0.004181 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    verifying project\ninmanta.env              WARNING Incompatibility between constraint python-slugify<7,>=6 and installed version 7.0.0 (from pyadr)\ninmanta.module           DEBUG   Loading module inmanta_plugins.std.resources\ninmanta.loader           DEBUG   Loading module: inmanta_plugins.std\ninmanta.module           DEBUG   Loading module inmanta_plugins.std\ninmanta.module           DEBUG   Parsing took 0.000092 seconds\ninmanta.parser.cache     DEBUG   Compiler cache observed 2 hits and 0 misses (100%)\ninmanta.module           INFO    The following modules are currently installed:\ninmanta.module           INFO    V1 modules:\ninmanta.module           INFO      std: 4.1.1\ninmanta.execute.schedulerDEBUG   Iteration 1 (e: 8, w: 0, p: 0, done: 0, time: 0.002478)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 1, w: 0, p: 0, done: 73, time: 0.001599)\ninmanta.execute.schedulerDEBUG   Finishing statements with no waiters\ninmanta.execute.schedulerDEBUG   Iteration 2 (e: 0, w: 0, p: 0, done: 74, time: 0.000229)\ninmanta.execute.schedulerINFO    Total compilation time 0.004449\ninmanta.compiler         DEBUG   Compile done\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\nasyncio                  DEBUG   Using selector: EpollSelector\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v2/reserve_version\ninmanta.protocol.endpointsDEBUG   Start transport for client compiler\ninmanta.export           INFO    Sending resources and handler source to server\ninmanta.export           INFO    Uploading source files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v1/file\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/codebatched/2\ninmanta.export           INFO    Uploading 1 files\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server POST http://localhost:55709/api/v1/file\ninmanta.export           INFO    Only 0 files are new and need to be uploaded\ninmanta.export           INFO    Sending resource updates to server\ninmanta.export           DEBUG     std::File[localhost,path=/tmp/test],v=2\ninmanta.export           DEBUG     std::AgentConfig[internal,agentname=localhost],v=2\ninmanta.protocol.rest.clientDEBUG   Getting config in section compiler_rest_transport\ninmanta.protocol.rest.clientDEBUG   Calling server PUT http://localhost:55709/api/v1/version\ninmanta.export           INFO    Committed resources with version 2\n	0	e76953a2-7688-4e98-a38c-4a5adac3689c
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resource (environment, model, resource_id, agent, last_deploy, attributes, attribute_hash, status, provides, resource_type, resource_id_value, last_non_deploying_status, resource_set) FROM stdin;
f7d137a1-c720-4ff2-817c-9e9231e279ba	1	std::File[localhost,path=/tmp/test]	localhost	2023-01-19 14:31:00.294462+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 1, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
f7d137a1-c720-4ff2-817c-9e9231e279ba	1	std::AgentConfig[internal,agentname=localhost]	internal	2023-01-19 14:31:01.689956+01	{"uri": "local:", "purged": false, "version": 1, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
f7d137a1-c720-4ff2-817c-9e9231e279ba	2	std::AgentConfig[internal,agentname=localhost]	internal	2023-01-19 14:31:09.026359+01	{"uri": "local:", "purged": false, "version": 2, "requires": [], "agentname": "localhost", "autostart": true, "send_event": false, "purge_on_delete": false}	57a3c0cc2657fc65ab59ca7c97f52d80	deployed	{"std::File[localhost,path=/tmp/test]"}	std::AgentConfig	localhost	deployed	\N
f7d137a1-c720-4ff2-817c-9e9231e279ba	2	std::File[localhost,path=/tmp/test]	localhost	2023-01-19 14:31:09.048281+01	{"hash": "7110eda4d09e062aa5e4a390b0a572ac0d2c0220", "path": "/tmp/test", "group": "root", "owner": "root", "purged": false, "reload": false, "version": 2, "requires": ["std::AgentConfig[internal,agentname=localhost]"], "send_event": false, "permissions": 644, "purge_on_delete": false}	af78dd949dae28f78c1acf515ca0beec	failed	{}	std::File	/tmp/test	failed	\N
\.


--
-- Data for Name: resourceaction; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction (action_id, action, started, finished, messages, status, changes, change, environment, version, resource_version_ids) FROM stdin;
3f5b4867-8659-4391-996d-47c60c02e2da	store	2023-01-19 14:30:59.182408+01	2023-01-19 14:30:59.190216+01	{"{\\"msg\\": \\"Successfully stored version 1\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 1}, \\"timestamp\\": \\"2023-01-19T14:30:59.190226+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::File[localhost,path=/tmp/test],v=1","std::AgentConfig[internal,agentname=localhost],v=1"}
4e2b3980-c186-4bf7-b7c3-f768cb669c7e	pull	2023-01-19 14:30:59.604676+01	2023-01-19 14:30:59.613336+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-01-19T14:30:59.613347+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
487e8461-5a6a-4f80-bd0b-85814f7598ae	deploy	2023-01-19 14:30:59.645886+01	2023-01-19 14:30:59.663134+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-01-19 14:30:59+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-01-19 14:30:59+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"fbe3f227-ee3e-427d-95e5-5b91d675ca08\\"}, \\"timestamp\\": \\"2023-01-19T14:30:59.642563+01:00\\"}","{\\"msg\\": \\"Start deploy fbe3f227-ee3e-427d-95e5-5b91d675ca08 of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"fbe3f227-ee3e-427d-95e5-5b91d675ca08\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-01-19T14:30:59.648141+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:30:59.648935+01:00\\"}","{\\"msg\\": \\"Calling create_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:30:59.652821+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy fbe3f227-ee3e-427d-95e5-5b91d675ca08\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"fbe3f227-ee3e-427d-95e5-5b91d675ca08\\"}, \\"timestamp\\": \\"2023-01-19T14:30:59.656796+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
97986919-4bdd-4754-818b-d6ae9a2a917d	pull	2023-01-19 14:31:00.184525+01	2023-01-19 14:31:00.186306+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.186332+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::File[localhost,path=/tmp/test],v=1"}
2d026aaf-6d9d-4687-b95d-d007042a83e0	deploy	2023-01-19 14:31:00.207885+01	2023-01-19 14:31:00.214765+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because Repair run started at 2023-01-19 14:31:00+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"Repair run started at 2023-01-19 14:31:00+0100\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"229769c9-5c67-41a9-ae7a-bd2494597ff9\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.205042+01:00\\"}","{\\"msg\\": \\"Start deploy 229769c9-5c67-41a9-ae7a-bd2494597ff9 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"229769c9-5c67-41a9-ae7a-bd2494597ff9\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:00.210090+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:31:00.210596+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-01-19T14:31:00.212140+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp7itao176/f7d137a1-c720-4ff2-817c-9e9231e279ba/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:00.212536+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 229769c9-5c67-41a9-ae7a-bd2494597ff9\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"229769c9-5c67-41a9-ae7a-bd2494597ff9\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.212737+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::File[localhost,path=/tmp/test],v=1"}
bbe724ae-c6ed-4173-9e91-47e08749e16e	pull	2023-01-19 14:31:00.264696+01	2023-01-19 14:31:00.266508+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.266517+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::File[localhost,path=/tmp/test],v=1"}
a77d8acc-0f2a-4e3f-b409-fc97d1271e17	deploy	2023-01-19 14:31:00.285903+01	2023-01-19 14:31:00.294462+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=1 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8e0ac15b-1d17-4b00-b432-41220c8a40e3\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.277484+01:00\\"}","{\\"msg\\": \\"Start deploy 8e0ac15b-1d17-4b00-b432-41220c8a40e3 of resource std::File[localhost,path=/tmp/test],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"8e0ac15b-1d17-4b00-b432-41220c8a40e3\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:00.287847+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:31:00.288688+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-01-19T14:31:00.290942+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=1 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp7itao176/f7d137a1-c720-4ff2-817c-9e9231e279ba/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:00.291112+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=1 in deploy 8e0ac15b-1d17-4b00-b432-41220c8a40e3\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=1\\", \\"deploy_id\\": \\"8e0ac15b-1d17-4b00-b432-41220c8a40e3\\"}, \\"timestamp\\": \\"2023-01-19T14:31:00.291304+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=1": {"std::File[localhost,path=/tmp/test],v=1": {"current": null, "desired": null}}}	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::File[localhost,path=/tmp/test],v=1"}
0fc0b26d-0730-4d26-8a6c-ec9310400678	deploy	2023-01-19 14:31:09.026359+01	2023-01-19 14:31:09.026359+01	{"{\\"msg\\": \\"Setting deployed due to known good status\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"timestamp\\": \\"2023-01-19T13:31:09.026359+00:00\\"}"}	deployed	\N	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	2	{"std::AgentConfig[internal,agentname=localhost],v=2"}
c7853566-fd5a-41b5-bd29-966568d25606	pull	2023-01-19 14:31:01.671611+01	2023-01-19 14:31:01.672512+01	{"{\\"msg\\": \\"Resource version pulled by client for agent internal state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"internal\\"}, \\"timestamp\\": \\"2023-01-19T14:31:01.672523+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
594f06a7-3a44-4656-8740-3e57a2a0b755	deploy	2023-01-19 14:31:01.682336+01	2023-01-19 14:31:01.689956+01	{"{\\"msg\\": \\"Start run for resource std::AgentConfig[internal,agentname=localhost],v=1 because Repair run started at 2023-01-19 14:31:01+0100\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"internal\\", \\"reason\\": \\"Repair run started at 2023-01-19 14:31:01+0100\\", \\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b0de290f-ad01-4a23-b924-5400fddfaa5b\\"}, \\"timestamp\\": \\"2023-01-19T14:31:01.679929+01:00\\"}","{\\"msg\\": \\"Start deploy b0de290f-ad01-4a23-b924-5400fddfaa5b of resource std::AgentConfig[internal,agentname=localhost],v=1\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"b0de290f-ad01-4a23-b924-5400fddfaa5b\\", \\"resource_id\\": {\\"version\\": 1, \\"attribute\\": \\"agentname\\", \\"agent_name\\": \\"internal\\", \\"entity_type\\": \\"std::AgentConfig\\", \\"attribute_value\\": \\"localhost\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:01.683773+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:31:01.684272+01:00\\"}","{\\"msg\\": \\"End run for resource std::AgentConfig[internal,agentname=localhost],v=1 in deploy b0de290f-ad01-4a23-b924-5400fddfaa5b\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::AgentConfig[internal,agentname=localhost],v=1\\", \\"deploy_id\\": \\"b0de290f-ad01-4a23-b924-5400fddfaa5b\\"}, \\"timestamp\\": \\"2023-01-19T14:31:01.687659+01:00\\"}"}	deployed	{"std::AgentConfig[internal,agentname=localhost],v=1": {"std::AgentConfig[internal,agentname=localhost],v=1": {"current": null, "desired": null}}}	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	1	{"std::AgentConfig[internal,agentname=localhost],v=1"}
263236a8-ee12-4b69-b94b-a53c40ff39e0	store	2023-01-19 14:31:09.0117+01	2023-01-19 14:31:09.013185+01	{"{\\"msg\\": \\"Successfully stored version 2\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"version\\": 2}, \\"timestamp\\": \\"2023-01-19T14:31:09.013193+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	2	{"std::File[localhost,path=/tmp/test],v=2","std::AgentConfig[internal,agentname=localhost],v=2"}
8b4de4fa-7f73-41ad-8e38-92f3d4e950ae	pull	2023-01-19 14:31:09.024827+01	2023-01-19 14:31:09.026189+01	{"{\\"msg\\": \\"Resource version pulled by client for agent localhost state\\", \\"args\\": [], \\"level\\": \\"INFO\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\"}, \\"timestamp\\": \\"2023-01-19T14:31:09.027040+01:00\\"}"}	\N	\N	\N	f7d137a1-c720-4ff2-817c-9e9231e279ba	2	{"std::File[localhost,path=/tmp/test],v=2"}
f6174f51-8b21-45f1-9122-f2b62a66a1b8	deploy	2023-01-19 14:31:09.041829+01	2023-01-19 14:31:09.048281+01	{"{\\"msg\\": \\"Start run for resource std::File[localhost,path=/tmp/test],v=2 because call to trigger_update\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"agent\\": \\"localhost\\", \\"reason\\": \\"call to trigger_update\\", \\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"7f45ae36-3f64-4f24-9797-1fe87ed84169\\"}, \\"timestamp\\": \\"2023-01-19T14:31:09.036661+01:00\\"}","{\\"msg\\": \\"Start deploy 7f45ae36-3f64-4f24-9797-1fe87ed84169 of resource std::File[localhost,path=/tmp/test],v=2\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"deploy_id\\": \\"7f45ae36-3f64-4f24-9797-1fe87ed84169\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:09.043124+01:00\\"}","{\\"msg\\": \\"Calling read_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {}, \\"timestamp\\": \\"2023-01-19T14:31:09.043515+01:00\\"}","{\\"msg\\": \\"Calling update_resource\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"changes\\": {\\"group\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}, \\"owner\\": {\\"current\\": \\"arnaud\\", \\"desired\\": \\"root\\"}}}, \\"timestamp\\": \\"2023-01-19T14:31:09.045446+01:00\\"}","{\\"msg\\": \\"An error occurred during deployment of std::File[localhost,path=/tmp/test],v=2 (exception: PermissionError('[Errno 1] Operation not permitted: '/tmp/test''))\\", \\"args\\": [], \\"level\\": \\"ERROR\\", \\"kwargs\\": {\\"exc_info\\": true, \\"exception\\": \\"PermissionError('[Errno 1] Operation not permitted: '/tmp/test'')\\", \\"traceback\\": \\"Traceback (most recent call last):\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/handler.py\\\\\\", line 936, in execute\\\\n    self.update_resource(ctx, dict(changes), desired)\\\\n  File \\\\\\"/tmp/tmp7itao176/f7d137a1-c720-4ff2-817c-9e9231e279ba/agent/code/modules/std/plugins/resources/__init__.py\\\\\\", line 221, in update_resource\\\\n    self._io.chown(resource.path, resource.owner, resource.group)\\\\n  File \\\\\\"/home/arnaud/Documents/projects/inmanta-core/src/inmanta/agent/io/local.py\\\\\\", line 605, in chown\\\\n    os.chown(path, _user, _group)\\\\nPermissionError: [Errno 1] Operation not permitted: '/tmp/test'\\\\n\\", \\"resource_id\\": {\\"version\\": 2, \\"attribute\\": \\"path\\", \\"agent_name\\": \\"localhost\\", \\"entity_type\\": \\"std::File\\", \\"attribute_value\\": \\"/tmp/test\\"}}, \\"timestamp\\": \\"2023-01-19T14:31:09.045665+01:00\\"}","{\\"msg\\": \\"End run for resource std::File[localhost,path=/tmp/test],v=2 in deploy 7f45ae36-3f64-4f24-9797-1fe87ed84169\\", \\"args\\": [], \\"level\\": \\"DEBUG\\", \\"kwargs\\": {\\"resource\\": \\"std::File[localhost,path=/tmp/test],v=2\\", \\"deploy_id\\": \\"7f45ae36-3f64-4f24-9797-1fe87ed84169\\"}, \\"timestamp\\": \\"2023-01-19T14:31:09.045882+01:00\\"}"}	failed	{"std::File[localhost,path=/tmp/test],v=2": {"std::File[localhost,path=/tmp/test],v=2": {"current": null, "desired": null}}}	nochange	f7d137a1-c720-4ff2-817c-9e9231e279ba	2	{"std::File[localhost,path=/tmp/test],v=2"}
\.


--
-- Data for Name: resourceaction_resource; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.resourceaction_resource (environment, resource_action_id, resource_id, resource_version) FROM stdin;
f7d137a1-c720-4ff2-817c-9e9231e279ba	3f5b4867-8659-4391-996d-47c60c02e2da	std::File[localhost,path=/tmp/test]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	3f5b4867-8659-4391-996d-47c60c02e2da	std::AgentConfig[internal,agentname=localhost]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	4e2b3980-c186-4bf7-b7c3-f768cb669c7e	std::AgentConfig[internal,agentname=localhost]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	487e8461-5a6a-4f80-bd0b-85814f7598ae	std::AgentConfig[internal,agentname=localhost]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	97986919-4bdd-4754-818b-d6ae9a2a917d	std::File[localhost,path=/tmp/test]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	2d026aaf-6d9d-4687-b95d-d007042a83e0	std::File[localhost,path=/tmp/test]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	bbe724ae-c6ed-4173-9e91-47e08749e16e	std::File[localhost,path=/tmp/test]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	a77d8acc-0f2a-4e3f-b409-fc97d1271e17	std::File[localhost,path=/tmp/test]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	c7853566-fd5a-41b5-bd29-966568d25606	std::AgentConfig[internal,agentname=localhost]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	594f06a7-3a44-4656-8740-3e57a2a0b755	std::AgentConfig[internal,agentname=localhost]	1
f7d137a1-c720-4ff2-817c-9e9231e279ba	263236a8-ee12-4b69-b94b-a53c40ff39e0	std::File[localhost,path=/tmp/test]	2
f7d137a1-c720-4ff2-817c-9e9231e279ba	263236a8-ee12-4b69-b94b-a53c40ff39e0	std::AgentConfig[internal,agentname=localhost]	2
f7d137a1-c720-4ff2-817c-9e9231e279ba	8b4de4fa-7f73-41ad-8e38-92f3d4e950ae	std::File[localhost,path=/tmp/test]	2
f7d137a1-c720-4ff2-817c-9e9231e279ba	0fc0b26d-0730-4d26-8a6c-ec9310400678	std::AgentConfig[internal,agentname=localhost]	2
f7d137a1-c720-4ff2-817c-9e9231e279ba	f6174f51-8b21-45f1-9122-f2b62a66a1b8	std::File[localhost,path=/tmp/test]	2
\.


--
-- Data for Name: schemamanager; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.schemamanager (name, legacy_version, installed_versions) FROM stdin;
core	\N	{1,2,3,4,5,6,7,17,202105170,202106080,202106210,202109100,202111260,202203140,202203160,202205250,202206290,202208180,202208190,202209090,202209130,202209160,202211230,202212010,202301100,202301110,202301120,202301160,202301170,202301190}
\.


--
-- Data for Name: unknownparameter; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.unknownparameter (id, name, environment, source, resource_id, version, metadata, resolved) FROM stdin;
\.


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
-- Name: code code_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.code
    ADD CONSTRAINT code_pkey PRIMARY KEY (environment, version, resource);


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
-- Name: resource resource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_pkey PRIMARY KEY (environment, model, resource_id);


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
-- Name: agent_id_primary_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX agent_id_primary_index ON public.agent USING btree (id_primary) WHERE (id_primary IS NULL);


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
-- Name: resource_attributes_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_attributes_index ON public.resource USING gin (attributes jsonb_path_ops);


--
-- Name: resource_env_attr_hash_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_attr_hash_index ON public.resource USING btree (environment, attribute_hash);


--
-- Name: resource_env_model_agent_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_env_model_agent_index ON public.resource USING btree (environment, model, agent);


--
-- Name: resource_env_resourceid_index; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX resource_env_resourceid_index ON public.resource USING btree (environment, resource_id, model DESC);


--
-- Name: resource_environment_resource_id_value_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_id_value_index ON public.resource USING btree (environment, resource_id_value);


--
-- Name: resource_environment_resource_type_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_resource_type_index ON public.resource USING btree (environment, resource_type);


--
-- Name: resource_environment_status_model_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resource_environment_status_model_idx ON public.resource USING btree (environment, status, model DESC);


--
-- Name: resourceaction_environment_action_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_action_started_index ON public.resourceaction USING btree (environment, action, started DESC);


--
-- Name: resourceaction_environment_version_started_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX resourceaction_environment_version_started_index ON public.resourceaction USING btree (environment, version, started DESC);


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
-- Name: code code_environment_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.code
    ADD CONSTRAINT code_environment_fkey FOREIGN KEY (environment) REFERENCES public.environment(id) ON DELETE CASCADE;


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
-- Name: resource resource_environment_model_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resource
    ADD CONSTRAINT resource_environment_model_fkey FOREIGN KEY (environment, model) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction resourceaction_environment_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction
    ADD CONSTRAINT resourceaction_environment_version_fkey FOREIGN KEY (environment, version) REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;


--
-- Name: resourceaction_resource resourceaction_resource_environment_resource_id_resource_v_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_environment_resource_id_resource_v_fkey FOREIGN KEY (environment, resource_id, resource_version) REFERENCES public.resource(environment, resource_id, model) ON DELETE CASCADE;


--
-- Name: resourceaction_resource resourceaction_resource_resource_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resourceaction_resource
    ADD CONSTRAINT resourceaction_resource_resource_action_id_fkey FOREIGN KEY (resource_action_id) REFERENCES public.resourceaction(action_id) ON DELETE CASCADE;


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
-- PostgreSQL database dump complete
--

